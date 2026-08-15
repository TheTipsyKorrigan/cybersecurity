import logging
import json
import os
from smartcard.util import toHexString, toBytes
from smartcard.ATR import ATR


class ReadData:
    AID = {
        "VISA":         [0xA0, 0x00, 0x00, 0x00, 0x03, 0x10, 0x10],
        "MASTERCARD":   [0xA0, 0x00, 0x00, 0x00, 0x04, 0x10, 0x10],
        "VPAY":         [0xA0, 0x00, 0x00, 0x00, 0x03, 0x20, 0x20],
        "EDENRED":      [0xA0, 0x00, 0x00, 0x04, 0x36, 0x01, 0x00],
        "CARTEVITALEx": [0xE8, 0x28, 0xBD, 0x08, 0x0F, 0xD2, 0x50, 0x00, 0x00, 0x04, 0x41, 0x64, 0xE8, 0x6C, 0x65],
        "CARTEVITALEy": [0xD2, 0x50, 0x00, 0x00, 0x02, 0x56, 0x49, 0x54, 0x41, 0x4C, 0x45],
        "CARTEVITALEz": [0xD2, 0x50, 0x00, 0x00, 0x04, 0x41, 0x64, 0xE8, 0x6C, 0x65, 0x01, 0x01],
    }

    def __init__(self, connection, card_type=None):
        self.connection = connection
        self.card_type = card_type
        responses_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apdu_responses.json')
        with open(responses_path) as f:
            self._apdu_responses = json.load(f)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def atr_content(self):
        """
        The Answer To Reset (ATR) is described in the ISO7816-3 standard.
        The first bytes describe the voltage convention, followed by interface
        bytes and historical bytes.
        """
        atr = ATR(self.connection.getATR())
        print("--------------------------------------------------------------------------")
        print("Answer To Reset: " + str(atr))
        print("Historical bytes:", toHexString(atr.getHistoricalBytes()))
        if atr.hasChecksum:
            print("Checksum: 0x%x" % atr.getChecksum())
            print("Checksum OK:", atr.checksumOK)
        else:
            print("No checksum set")
        print("T0  supported:", atr.isT0Supported())
        print("T1  supported:", atr.isT1Supported())
        print("T15 supported:", atr.isT15Supported())
        print("--------------------------------------------------------------------------")

    def card_content(self):
        """
        Select an application on the card.
        - If card_type is set: selects that specific AID directly.
        - Otherwise: tries PSE discovery first, then falls back to the AID dictionary.
        Returns True if an application was successfully selected.
        """
        if self.card_type:
            candidates = [(self.AID[self.card_type], self.card_type)]
        else:
            candidates = self._discover_via_pse() or [
                (aid, name) for name, aid in self.AID.items()
            ]

        for aid_bytes, label in candidates:
            apdu = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes) + [0x00]
            try:
                data, sw1, sw2 = self.connection.transmit(apdu)

                if sw1 == 0x61:
                    _, sw1, sw2 = self.connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])

                desc = self.get_apdu_response(sw1, sw2)
                print("%-20s | %02X %02X: %s - %s" % (label, sw1, sw2, desc[0], desc[1]))

                if sw1 == 0x90:
                    self.card_type = label
                    return True
            except Exception as e:
                logging.error("Error selecting %s: %s" % (label, e))

        print("No known application found on this card.")
        return False

    def read_file_structure(self):
        """
        Brute-forces Short File Identifiers (SFI 1-39) and records (1-16) via READ RECORD.
        Stops scanning a SFI when a record is not found, and aborts entirely if the
        instruction is not supported.
        """
        for sfi in range(1, 40):
            for rec in range(1, 17):
                p1 = rec
                p2 = (sfi << 3) | 4
                data, sw1, sw2 = self.connection.transmit([0x00, 0xB2, p1, p2, 0x00])

                if sw1 == 0x6A and sw2 == 0x83:
                    logging.debug("SFI %02d | rec %02d: record not found" % (sfi, rec))
                    break

                elif sw1 == 0x6D and sw2 == 0x00:
                    print("READ RECORD not supported on this card.")
                    return

                elif sw1 == 0x6C:
                    data, sw1, sw2 = self.connection.transmit([0x00, 0xB2, p1, p2, sw2])
                    if sw1 == 0x90:
                        self._print_record(sfi, rec, data)

                elif sw1 == 0x90:
                    self._print_record(sfi, rec, data)

                else:
                    logging.debug("SFI %02d | rec %02d: %02X %02X" % (sfi, rec, sw1, sw2))

    def get_apdu_response(self, sw1, sw2):
        hex_sw1 = "%02X" % sw1
        hex_sw2 = "%02X" % sw2
        entry = self._apdu_responses.get(hex_sw1, {})
        response_type = entry.get("type", "Unknown")
        if hex_sw1 in ("61", "6C"):
            description = entry.get("XX", "").replace("XX", hex_sw2)
        else:
            description = entry.get(hex_sw2, "Unknown response")
        return response_type, description

    # -------------------------------------------------------------------------
    # PSE discovery
    # -------------------------------------------------------------------------

    def _discover_via_pse(self):
        """
        Discover AIDs using the Payment System Environment directory.
        Tries the contact PSE (1PAY.SYS.DDF01) then contactless (2PAY.SYS.DDF01).
        Returns a list of (aid_bytes, label) tuples, or None if PSE is not supported.
        """
        for pse_name in ["1PAY.SYS.DDF01", "2PAY.SYS.DDF01"]:
            aids = self._read_pse(pse_name)
            if aids is not None:
                return aids
        return None

    def _read_pse(self, pse_name):
        """
        Select a PSE directory and read its records to collect AIDs.
        Returns a list of (aid_bytes, label) tuples, or None if not found/supported.
        """
        pse_bytes = [ord(c) for c in pse_name]
        apdu = [0x00, 0xA4, 0x04, 0x00, len(pse_bytes)] + pse_bytes + [0x00]
        data, sw1, sw2 = self.connection.transmit(apdu)

        if sw1 == 0x61:
            data, sw1, sw2 = self.connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])

        if sw1 != 0x90:
            return None

        print("PSE found: %s" % pse_name)

        # FCI contains tag 88 = SFI of the directory file
        sfi_data = self._tlv_find(data, 0x88)
        if not sfi_data:
            return None

        sfi = sfi_data[0]
        aids = []

        for rec in range(1, 17):
            p2 = (sfi << 3) | 4
            rec_data, sw1, sw2 = self.connection.transmit([0x00, 0xB2, rec, p2, 0x00])

            if sw1 == 0x6C:
                rec_data, sw1, sw2 = self.connection.transmit([0x00, 0xB2, rec, p2, sw2])

            if sw1 == 0x6A and sw2 == 0x83:
                break

            if sw1 != 0x90:
                continue

            # Each record is a 70 template containing 61 application templates.
            # Each 61 contains: 4F (AID), 50 (label), 87 (priority).
            for app in self._tlv_find_all(rec_data, 0x61):
                aid_bytes = self._tlv_find(app, 0x4F)
                label_bytes = self._tlv_find(app, 0x50)
                if aid_bytes:
                    label = bytes(label_bytes).decode('ascii', errors='replace') if label_bytes else toHexString(list(aid_bytes))
                    print("  Discovered: %-20s %s" % (label, toHexString(list(aid_bytes))))
                    aids.append((list(aid_bytes), label))

        return aids if aids else None

    # -------------------------------------------------------------------------
    # TLV helpers
    # -------------------------------------------------------------------------

    def _tlv_parse(self, data):
        """Parse a TLV sequence into a list of (tag, value) tuples."""
        result = []
        i = 0
        while i < len(data):
            tag = data[i]
            i += 1
            # Multi-byte tag: lower 5 bits all set means tag continues
            if (tag & 0x1F) == 0x1F:
                while i < len(data):
                    b = data[i]
                    tag = (tag << 8) | b
                    i += 1
                    if not (b & 0x80):
                        break

            if i >= len(data):
                break

            # Length
            l = data[i]
            i += 1
            if l & 0x80:
                num_bytes = l & 0x7F
                l = 0
                for _ in range(num_bytes):
                    if i >= len(data):
                        break
                    l = (l << 8) | data[i]
                    i += 1

            value = data[i:i + l]
            result.append((tag, value))
            i += l

        return result

    def _tlv_find(self, data, target_tag):
        """Return the value of the first occurrence of target_tag, searching recursively."""
        for tag, value in self._tlv_parse(data):
            if tag == target_tag:
                return value
            if tag & 0x20:  # constructed tag — search inside
                result = self._tlv_find(value, target_tag)
                if result is not None:
                    return result
        return None

    def _tlv_find_all(self, data, target_tag):
        """Return values of all occurrences of target_tag, searching recursively."""
        results = []
        for tag, value in self._tlv_parse(data):
            if tag == target_tag:
                results.append(value)
            if tag & 0x20:
                results.extend(self._tlv_find_all(value, target_tag))
        return results

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _print_record(self, sfi, rec, data):
        hex_str = toHexString(data)
        ascii_str = ''.join(chr(b) if 0x20 <= b <= 0x7E else '.' for b in data)
        print("SFI %02d | Rec %02d | hex: %s" % (sfi, rec, hex_str))
        print("              | asc: %s" % ascii_str)
