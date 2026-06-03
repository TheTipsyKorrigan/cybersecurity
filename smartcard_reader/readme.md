# SmartCard Reader

A Python learning project for interacting with ISO 7816 smart cards (payment cards, SIM cards, health cards) via a physical card reader, using the [pyscard](https://pyscard.sourceforge.io/) library.

## References
- [pyscard user guide](https://pyscard.sourceforge.io/user-guide.html)
- [ISO 7816 smart card standards](https://cardwerk.com/smart-card-standards/)
- [APDU command reference](http://web.archive.org/web/20100811204535/http://cheef.ru/docs/HowTo/APDU.table)
- [Complete list of APDU responses](https://www.eftlab.com/knowledge-base/complete-list-of-apdu-responses)
- [EMV read flow](https://www.openscdp.org/scripts/tutorial/emv/reademv.html)
- [ATR parser](https://smartcard-atr.apdu.fr/)

## Project Structure

### Main program

**`main.py`** — Entry point. Connects to the first available reader and runs three operations on a VISA card:
1. Reads and parses the ATR
2. Selects the VISA application via its AID
3. Brute-forces the card's file structure

**`read_card.py`** — Core `ReadData` class:
- `atr_content()` — Parses the Answer To Reset (ISO 7816-3): historical bytes, checksum, and supported protocols (T=0, T=1, T=15)
- `card_content()` — Sends a `SELECT` APDU (`0xA4`) with the card's Application Identifier to activate the payment app
- `read_file_structure()` — Iterates all Short File Identifiers (SFI 1–39) and records (1–16) via `READ RECORD` (`0xB2`), handling `6C XX` (wrong length) by retrying with the correct length
- `get_app_identifier()` — AID table for VISA, Mastercard, VPay, Edenred, and Carte Vitale variants
- `get_adpu_response()` — Resolves SW1/SW2 status words to human-readable descriptions via `apdu_responses.json`

**`bruteforce_typecard.py`** — Accepts any card and prints its ATR and protocol.

**`apdu_responses.json`** — Status word lookup table (SW1/SW2 → description).

### Learning scripts

Progressive exercises exploring the pyscard API:

| Script | Topic |
|---|---|
| `script_02.py` | Accept any card, print ATR and protocol |
| `script_03.py` | Match a card by exact ATR, select a Telecom DF |
| `script_4.py` | Custom `CardType` — match cards by first ATR byte (direct convention `0x3B`) |
| `script_5.py` | Force T=0 protocol on connect |
| `script_6.py` | T=0 with `GET RESPONSE` follow-up when SW1 = `0x9F` |

## Key Concepts

- **ATR** — the card's hello message describing its communication parameters (ISO 7816-3)
- **APDU** — the command/response protocol: `[CLA, INS, P1, P2, Lc, Data..., Le]`
- **AID selection** — how to activate a specific payment application on a multi-app card
- **File system** — MF → ADF → AEF tree structure, navigated by Short File Identifier (SFI)
- **Status words** — SW1/SW2 two-byte response codes (e.g. `90 00` = success, `6A 83` = record not found, `6C XX` = wrong length)
- **Protocols** — T=0 (byte-oriented) and T=1 (block-oriented) transmission protocols

## Requirements

```
pyscard
```

## Usage

Insert a card into a connected reader, then:

```bash
python main.py
```

To use a different card type, change the `card_type` argument in `main.py`:

```python
card = ReadData(connection, "MASTERCARD")  # VISA, MASTERCARD, VPAY, EDENRED, CARTEVITALEx/y/z
```
