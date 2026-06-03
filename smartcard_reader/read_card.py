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

    def atr_content(self):
        """
        The Answer To Reset (ATR) is described in the ISO7816-3 standard.
        The first bytes describe the voltage convention (direct or inverse),
        followed by interface bytes and historical bytes.
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
        Select an application by AID. If card_type is None, tries all known AIDs.
        Returns True if an application was successfully selected.
        """
        candidates = [self.card_type] if self.card_type else list(self.AID.keys())

        for card_type in candidates:
            aid = self.AID[card_type]
            apdu = [0x00, 0xA4, 0x04, 0x00] + [len(aid)] + aid + [0x00]
            try:
                data, sw1, sw2 = self.connection.transmit(apdu)
                desc = self.get_apdu_response(sw1, sw2)
                print("%-15s | %02X %02X: %s - %s" % (card_type, sw1, sw2, desc[0], desc[1]))

                if sw1 == 0x90:
                    self.card_type = card_type
                    return True
                elif sw1 == 0x61:
                    # Data available — fetch it with GET RESPONSE
                    _, sw1, sw2 = self.connection.transmit([0x00, 0xC0, 0x00, 0x00, sw2])
                    if sw1 == 0x90:
                        self.card_type = card_type
                        return True
            except Exception as e:
                logging.error("Error selecting %s: %s" % (card_type, e))

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
                    # No more records for this SFI
                    logging.debug("SFI %02d | rec %02d: record not found" % (sfi, rec))
                    break

                elif sw1 == 0x6D and sw2 == 0x00:
                    # Card does not support READ RECORD at all
                    print("READ RECORD not supported on this card.")
                    return

                elif sw1 == 0x6C:
                    # Wrong Le — retry with the correct length indicated by sw2
                    data, sw1, sw2 = self.connection.transmit([0x00, 0xB2, p1, p2, sw2])
                    if sw1 != 0x90:
                        logging.debug("SFI %02d | rec %02d: retry failed (%02X %02X)" % (sfi, rec, sw1, sw2))
                        continue
                    self._print_record(sfi, rec, data)

                elif sw1 == 0x90:
                    self._print_record(sfi, rec, data)

                else:
                    logging.debug("SFI %02d | rec %02d: %02X %02X" % (sfi, rec, sw1, sw2))

    def _print_record(self, sfi, rec, data):
        hex_str = toHexString(data)
        ascii_str = ''.join(
            chr(b) if 0x20 <= b <= 0x7E else '.' for b in data
        )
        print("SFI %02d | Rec %02d | hex: %s" % (sfi, rec, hex_str))
        print("              | asc: %s" % ascii_str)

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
