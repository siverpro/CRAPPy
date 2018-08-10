"""
USAGE:
Initialize a FriPostering with description:
postering = FriPostering(description="ABC")

Initialize as many JournalEntries you want with description and ISO-date:
entry1 = JournalEntry(description="ABC", date="2018-01-01")
entry2 = JournalEntry(description="DEF", date="2018-02-02")

Add lines to your Journal entries (amount, debit account, credit account, vat code (defaults to 6))
entry1.addLine(300, "9191", "8181", "6")
entry2.addLine(500, "9111", "9999")

Add your entries to your post
postering.addEntry(entry1)
postering.addEntry(entry2)

Now you can retrieve a Fiken-friendy json:
postering.toJson()
"""

import json
from decimal import Decimal


class FriPostering(object):
	def __init__(self, description=None):
		self.postering = {"description": description, "journalEntries": []}
		self.entries = []
	
	def addEntry(self, description, date) -> int:
		self.entries.append({"description": description, "date": date, "lines": []})
		return len(self.entries) - 1
	
	def addLine(self, index, debit_amount, debit_account, credit_account, vat_code="6"):
		self.entries[index]["lines"].append({
			"debit": int(Decimal(debit_amount) * 100),
			"debitAccount": str(debit_account),
			"creditAccount": str(credit_account),
			"creditVatCode": str(vat_code)})
	
	def toJson(self):
		self.postering['journalEntries'] = self.entries
		return json.dumps(self.postering)
	
	def toDict(self):
		self.postering['journalEntries'] = self.entries
		return self.postering


