"""
Card-centric approach

Ref:
- smartcard library user guide: https://pyscard.sourceforge.io/user-guide.html#
- Smart card standards: https://cardwerk.com/smart-card-standards/
- APDU command list: http://web.archive.org/web/20100811204535/http://cheef.ru/docs/HowTo/APDU.table
- Complete list of APDU responses: https://www.eftlab.com/knowledge-base/complete-list-of-apdu-responses

https://www.openscdp.org/scripts/tutorial/emv/reademv.html
https://hpkaushik121.medium.com/understanding-apdu-commands-emv-transaction-flow-part-2-d4e8df07eec
https://en.wikipedia.org/wiki/EMV#Application_selection

"""
import logging
import sys
from smartcard.System import readers

from read_card import ReadData

LOG_FORMAT = "%(asctime)s: %(levelname)s - %(message)s"
logging.basicConfig(level=logging.CRITICAL, format=LOG_FORMAT)

r = readers()
print(r)

if not r:
    print("No card readers found.")
    sys.exit(1)

connection = r[0].createConnection()
connection.connect()

# Pass a card_type (e.g. "VISA") to target a specific app, or omit to auto-detect.
card = ReadData(connection)
card.atr_content()
if card.card_content():
    card.read_file_structure()
