#!/usr/bin/env python
# Built-in
import datetime
import json
from decimal import Decimal
from tqdm import tqdm
from FriPostering import FriPostering
# Own
from btctax import BtcTax
from db import Database
from fiken import Fiken

"""
- Mottatt FCT i wallet
	- NOK verdi av når det kom inn
	
- FCT til BTC
	- NOK verdi at BTC du fikk da du solgte - differansen er kapitalinntekt/tap
- BTC til EUR
	- Og NOK verdi av EUR når du solgte
"""


if __name__ == "__main__":
	# INITIALISATION
	###########################################################################################################
	# Load config file
	try:
		with open('conf.json') as json_data_file:
			config = json.load(json_data_file)
	except IOError as e:
		print(e)

	# 
	# Init Bitcoin TAX
	btc_tax = BtcTax(
		username=config["BITOOINTAX_USERNAME"],
		password=config["BITCOINTAX_PASSWORD"],
		api_key=config["BITCOINTAX_API_KEY"],
		api_secret=config["BITCOINTAX_API_SECRET"],
		debug=False)
	
	# Init DB
	db = Database(
		db_hostname=config["DB_HOSTNAME"],
		db_username=config["DB_USERNAME"],
		db_password=config["DB_PASSWORD"],
		db_dataname=config["DB_DATA_NAME"],
		db_table_income=config["DB_TABLE_INCOMES"],
		db_table_sales=config["DB_TABLE_SALES"],
		debug=False)
	
	# Init Fiken
	fiken = Fiken(
		user=config["FIKEN_USERNAME"],
		passwd=config["FIKEN_PASSWORD"],
		company_slug=config["FIKEN_COMPANY_SLUG"],
		debug_endpoint=True)
	
	CURRENCIES = ['EUR', 'USD']
	###########################################################################################################
	
	# Connect to db
	db.connect()

	# Get API data for incomes
	btcTax_data = btc_tax.get_transactions(taxyear=2018, start=0, limit=99999)

	# Set 2 days delay.
	end_date = datetime.date.today() - datetime.timedelta(days=2)
	SKIP = 1
	if SKIP:
		for row in tqdm(btcTax_data['transactions'], desc="Retrieving incomes"):

			# Wait 2 days until we process stuff
			income_time = datetime.datetime.fromisoformat(row['date'])

			if end_date > income_time.date():
				if row['action'] == "INCOME":
					# Calculate NOK value from EUR
					#rate = db.get_eur_rate(income_time.strftime("%Y-%m-%d"))

					rate = db.get_rate(income_time.strftime("%Y-%m-%d"), currency=row['currency'])
					nok_amount = row['volume'] * row['price'] * Decimal(rate)

					# Insert to database
					db.append_income(row['id'], row['date'], row['symbol'], row['volume'], nok_amount, row['txhash'])

		# Get sales data from CSV
		btcTax_csv = btc_tax.get_data()
		for row in tqdm(btcTax_csv['sales'], desc="Retrieving sales"):
			db.append_sales(
				(row['Date Sold'] + row['Symbol']),
				row['Date Sold'],
				row['Volume'],
				row['Symbol'],
				row['Proceeds'],
				row["Currency"])


	# INCOME
	###########################################################################################################
	unprocessed_incomes = db.get_unprocessed_incomes()
	# Loop through the transactions and fill the journal entries and lines to fit to fiken
	if unprocessed_incomes:
		# Create a journal entry for fiken
		postering = FriPostering(description="Import fra Bitcoin.tax")
		
		for row in unprocessed_incomes:
			description = "Inntekt - " + str(row["Amount"]) + " " + str(row["Symbol"])
			date = datetime.datetime.fromtimestamp(row["Timestamp"]).date()
			entry = postering.addEntry(description, str(date))
			line = postering.addLine(
				index=entry,
				debit_amount=row["NOK_Amount"],
				debit_account=config["FIKEN_ANNEN_VALUTA"],
				credit_account=config["FIKEN_FINANSINNTEKTSKONTO"],
				vat_code="6")
		
		# Retrieve valid json fit to fiken.
		valid_json = postering.toJson()

		# Post entries to fiken
		headers = fiken.post_til_fiken(valid_json)
		# If success, then mark these transactions as processed at DB.
		if headers["Location"]:
			for row in tqdm(unprocessed_incomes, desc="Processing incomes"):
				db.process_income(int(row["Income_ID"]))
				# print("transaction with ID: {} has been processed, updating DB..".format(int(row["Income_ID"])))
	else:
		print("No unprocessed transactions found.")
		
	# SALES
	###########################################################################################################
	# Retrieve unprocessed sales from database.
	unprocessed_sales = db.get_unprocessed_sales()
	# Loop through the transactions and fill the journal entries and lines to fit to fiken
	if unprocessed_sales:
		g_debit = None
		g_credit = None
		# Create a journal entry for fiken
		postering = FriPostering(description="Import fra Bitcoin.tax")
		
		for row in unprocessed_sales:
			description = "Salg - " + str(row["Sell_Amount"]) + " " + str(row["Sell_Currency"])
			date = row["Timestamp"]
			entry = postering.addEntry(description, date)

			rate = db.get_rate(row['Timestamp'], currency=row['Buy_Currency'])
			gains = Decimal(row["Buy_Amount"]) * Decimal(rate) - Decimal(row["Cost_Base"])
			postering.addLine(
				index=entry,
				debit_amount=row["Cost_Base"],
				debit_account=config["FIKEN_KUNDEKONTO"],
				credit_account=config["FIKEN_ANNEN_VALUTA"],
				vat_code="6")

			if gains >= 0:
				g_debit = config["FIKEN_KUNDEKONTO"]
				g_credit = config["FIKEN_AGIO_KONTO"]
			elif gains < 0:
				g_debit = config["FIKEN_DISAGIO_KONTO"]
				g_credit = config["FIKEN_KUNDEKONTO"]
			
			postering.addLine(
				index=entry,
				debit_amount=abs(gains),
				debit_account=g_debit,
				credit_account=g_credit,
				vat_code="6")
		
		# Retrieve valid json fit to fiken.
		valid_json = postering.toJson()
		
		# Post entries to fiken
		headers = fiken.post_til_fiken(valid_json)
		# If success, then mark these transactions as processed at DB.
		if headers["Location"]:
			for row in tqdm(unprocessed_sales, desc="Processing sales"):
				db.process_sale(int(row["Sale_ID"]))
				# print("Sale with ID: {} has been processed, updating DB..".format(int(row["Sale_ID"])))
	else:
		print("No unprocessed sales found.")
	
	# Done with database requests
	db.close_connection()
	