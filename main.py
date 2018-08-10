import json
import sys
from btctax import BtcTax
from db import Database
from fiken import Fiken
import decimal
import datetime

"""
- Mottatt FCT i wallet
	- NOK verdi av når det kom inn
	
- FCT til BTC
	- NOK verdi at BTC du fikk da du solgte - differansen er kapitalinntekt/tap
- BTC til EUR
	- Og NOK verdi av EUR når du solgte
"""


if __name__ == "__main__":
	# Initialisations
	###########################################################################################################
	# Load config file
	with open('conf.json') as json_data_file:
		config = json.load(json_data_file)
	
	# Init Bitcoin TAX
	btc_tax = BtcTax(
		username=config["BITOOINTAX_USERNAME"],
		password=config["BITCOINTAX_PASSWORD"],
		api_key=config["BITCOINTAX_API_KEY"],
		api_secret=config["BITCOINTAX_API_SECRET"],
		print=True)
	
	# Init DB
	db = Database(
		db_hostname=config["DB_HOSTNAME"],
		db_username=config["DB_USERNAME"],
		db_password=config["DB_PASSWORD"],
		db_dataname=config["DB_DATA_NAME"],
		print=True)
	
	# Init Fiken
	fiken = Fiken(
		user=config["FIKEN_USERNAME"],
		passwd=config["FIKEN_PASSWORD"],
		company_slug=config["FIKEN_COMPANY_SLUG"])
	
	CURRENCIES = ['EUR', 'USD']
	###########################################################################################################
	
	# Connect to db
	db.connect()
	
	# Get the data
	btcTax_data = btc_tax.get_transactions(taxyear=2018, start=0, limit=1000)
	
	print("Processing incomes and sales:")
	end_date = datetime.date.today() - datetime.timedelta(days=2)
	for row in btcTax_data['transactions'][::-1]:

		# Wait 2 days until we process stuff
		income_time = datetime.datetime.fromisoformat(row['date'])
	
		if end_date > income_time.date():
			# Incomes
			if row['action'] == "INCOME":
				# Calculate NOK value from EUR
				rate = db.get_eur_rate(income_time.strftime("%Y-%m-%d"))
				nok_amount = row['volume'] * row['price'] * decimal.Decimal(rate)

				# Insert to database
				db.append_income(
					row['id'],
					row['date'],
					row['symbol'],
					row['volume'],
					nok_amount,
					row['txhash'])
				
			# sales
			elif row['action'] == "SELL":
				if row['feecurrency'] == row['currency']:
					buy_amount = (row['volume'] * row['price']) - row['fee']
				elif row['feecurrency'] == row['symbol']:
					buy_amount = (row['volume'] - row['fee']) * row['price']
				else:
					buy_amount = row['volume'] * row['price']
				
				if row['currency'] in CURRENCIES:
					rate = db.get_rate_from_bank(income_time.strftime("%Y-%m-%d"), row['currency'])
					proceeds = buy_amount * decimal.Decimal(rate)
				else:
					proceeds = db.sell_currency(
						row['volume'],
						row['symbol'],
						income_time.strftime("%Y-%m-%d"))
		
				db.append_sales(
					row['id'],
					row['date'],
					row['volume'],
					row['symbol'],
					buy_amount,
					row['currency'],
					proceeds)
				
	db.close_connection()
	exit(0)
	
	