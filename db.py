import mysql.connector as mariadb

# Needed for norges bank
import datetime
import json
import requests


class DBError(Exception):
	"""
	Fange exceptions for invalide kommandoer og andre responser som
	ikke er en kode 200 respons.
	"""
	def __init__(self, err):
		pass


class Database(object):
	def __init__(self, db_hostname=None, db_username=None, db_password=None, db_dataname=None, print = False):
		if db_hostname:
			self.db_hostname = str(db_hostname)
		else:
			raise DBError("No hostname given.")
		
		if db_username:
			self.db_username = str(db_username)
		else:
			raise DBError("DB username is needed.")
	
		if db_password:
			self.db_password = str(db_password)
		else:
			raise DBError("DB password is needed.")
		
		if db_dataname:
			self.db_dataname = str(db_dataname)
		else:
			raise DBError("No database name is given.")
			
		self.print = print
		self.db_connection = None
		self.income_table = "Tx_Log"
		
	def connect(self):
		try:
			if self.print:
				print("Connecting to database with username: {}".format(self.db_username))
			self.db_connection = mariadb.connect(
				host=self.db_hostname,
				user=self.db_username,
				password=self.db_password,
				database=self.db_dataname)
			if self.print:
				print("Connected!")
		except Exception as e:
			print(str(e))
			exit(0)
			
	def close_connection(self):
		if self.print:
			print("Closing connection..")
		
		if self.db_connection is None:
			pass
		else:
			self.db_connection.close()
			self.db_connection = None
	
	def append_income(self, tax_id, timestamp, currency, amount, nok_amount, tx_hash) -> int:
		out = 0
		posixtime = datetime.datetime.fromisoformat(timestamp).timestamp()
		if self.income_exists(tax_id):
			if self.print:
				print("Transaction already exists, not appending")
		else:
			if self.print:
				print("New transaction found, appending!")
			cursor = self.db_connection.cursor()

			try:
				query = "INSERT INTO A_Incomes (Tax_ID, Timestamp, Symbol, Amount, NOK_Amount, Tx_Hash) "
				query += f"VALUES (\"{tax_id}\", {posixtime}, \"{currency}\", {amount}, {nok_amount}, \"{tx_hash}\")"
				cursor.execute(query)
			except Exception as e:
				raise DBError(str(e))
			
			self.db_connection.commit()
			out = cursor.lastrowid
			
		return out
	
	def income_exists(self, tax_id):
		out = True
		cursor = self.db_connection.cursor()
		
		query = f"SELECT Income_ID FROM A_Incomes WHERE Tax_ID=\"{tax_id}\" LIMIT 0,1"
		cursor.execute(query)
		
		# Check log files for duplicates
		if cursor.fetchone() is None:
			# return false if no match is found
			out = False
		return out
	
	def sale_exists(self, date, cost_base, proceeds, gains, foreign_amount, foreign_currency):
		out = True
		cursor = self.db_connection.cursor()
		
		query = "SELECT Sale_ID FROM A_Sales WHERE Date = %s AND Cost_Base = %s AND Proceeds = %s AND Gains = %s AND Foreign_Amount = %s AND Foreign_Currency = %s LIMIT 0,1"
		cursor.execute(query, (date, cost_base, proceeds, gains, foreign_amount, foreign_currency))
		# Check db for duplicates
		if cursor.fetchone() is None:
			# return false if no match is found
			out = False
		return out
	
	def append_sales_log(self, date, cost_base, proceeds, gains, foreign_amount, foreign_currency) -> int:
		out = 0
		
		if self.sale_exists(date, cost_base, proceeds, gains, foreign_amount, foreign_currency):
			if self.print:
				print("Sale already exists, not appending")
		else:
			if self.print:
				print("New sale found, appending!")
			cursor = self.db_connection.cursor()
			
			try:
				query = "INSERT INTO A_Sales (Date, Cost_Base, Proceeds, Gains, Foreign_Amount, Foreign_Currency) VALUES(%s, %s, %s, %s, %s, %s)"
				cursor.execute(query, (date, cost_base, proceeds, gains, foreign_amount, foreign_currency))
			except Exception as e:
				raise DBError(str(e))
			
			self.db_connection.commit()
			out = cursor.lastrowid
		return out
	
	def get_unprocessed_incomes(self):
		if self.print:
			print("Retrieving transactions not sent to Fiken...")
		cursor = self.db_connection.cursor(dictionary=True)
		cursor.execute("SELECT A_Incomes, Date, NOK_Amount, Foreign_Amount, Foreign_Currency FROM Tx_Log WHERE Processed = 0")
		
		return cursor.fetchall()

	def get_unprocessed_sales(self):
		if self.print:
			print("Retrieving sales not sent to Fiken...")
		cursor = self.db_connection.cursor(dictionary=True)
		cursor.execute("SELECT A_Sales, Date, Cost_Base, Proceeds, Gains, Foreign_Amount, Foreign_Currency FROM Sale_Log WHERE Processed = 0")
		return cursor.fetchall()

	def process_sale(self, sale_id):
		var = 1
		cursor = self.db_connection.cursor()
		try:
			query = "UPDATE A_Sales SET Processed=%s WHERE Sale_ID = %s"
			cursor.execute(query, (var, sale_id))
		except self.db_connection.Error as error:
			print("Error: {}".format(error))
			raise DBError(str(error))
		self.db_connection.commit()

	def process_income(self, tx_id):
		var = 1
		cursor = self.db_connection.cursor()
		try:
			query = "UPDATE A_Incomes SET Processed=%s WHERE Income_ID=%s"
			cursor.execute(query, (var, tx_id))
		except Exception as e:
			print("Error: {}".format(e))
			raise DBError(str(e))
		self.db_connection.commit()

	def get_last_income(self):
		cursor = self.db_connection.cursor(dictionary=True)
		query = "SELECT Tax_ID FROM A_Incomes ORDER BY Income_ID DESC LIMIT 0,1"
		cursor.execute(query)
		return cursor.fetchone()

	def get_balance(self, currency):
		cursor = self.db_connection.cursor(dictionary=True)
		query = f"SELECT SUM(Amount) AS Amount FROM A_Incomes WHERE Sell_Date IS NULL AND Symbol = \"{currency}\""
		cursor.execute(query)
		return cursor.fetchone()

	def sell_currency(self, amount, currency, date):
		cursor = self.db_connection.cursor(dictionary=True)
		query = "SELECT Income_ID, Amount FROM A_Incomes WHERE Sell_Date IS NULL "
		query += f"AND Symbol = \"{currency}\" ORDER BY Timestamp ASC"
		cursor.execute(query)
		unsold = cursor.fetchall()
		value = 0
		last_id = 0
		sold_ids = []
		for row in unsold:
			if value < amount:
				value += row['Amount']
				sold_ids.append(row['Income_ID']) # List of IDs to be sold
				last_id = row['Income_ID']
			else:
				break

		for id in sold_ids: # mark them as sold
			query = f"UPDATE A_Incomes SET Sell_Date = \"{date}\" WHERE Income_ID = {id}"
			cursor.execute(query)
		self.db_connection.commit() # The list has now been marked as sold

		if value == amount:
			# we're done if we have a match. if not we need to split an income.
			return
		elif value > amount:
			# The last income has to be split.
			diff = value - amount
			# The row that needs to be split
			query = f"SELECT * FROM A_Incomes WHERE Income_ID = {last_id}"
			cursor.execute(query)
			original_row = cursor.fetchone()

			remainder = original_row['Amount'] - diff # How much to leave in the original row
			query = f"UPDATE A_Incomes SET Amount = {remainder} WHERE Income_ID = {last_id}"
			cursor.execute(query)
			self.db_connection.commit() # Original row fixd.

			#Copy values into new income
			self.append_income(original_row['Tax_ID']+last_id, original_row['Timestamp'],
								original_row['Symbol'], diff, 0.0, original_row['Tx_Hash'])


	def get_eur_rate(self, isodate):
		query = f"SELECT Price FROM EUR WHERE Date=\"{isodate}\" LIMIT 0,1"
		cursor = self.db_connection.cursor(dictionary=True)
		try:
			cursor.execute(query)
		except Exception as e:
			print("Error: {e}")
			raise DBError(str(e))
		row = cursor.fetchone()
		if row is None:
			rate = self.get_rate_from_bank(isodate, "EUR")
			insert_query = f"INSERT INTO EUR (Date, Price) VALUES (\"{isodate}\", \"{rate}\")"
			cursor.execute(insert_query)
			self.db_connection.commit()
			return rate
		else:
			return row['Price']

	def get_rate_from_bank(self, date, currency):
		out = None
		dateobj = datetime.date.fromisoformat(date)
		today = datetime.date.today()
		if dateobj >= today:
			print("Date in the future. Exiting.")
			return out

		entry_nb = "https://data.norges-bank.no/api/data/EXR/"
		url = f"B.{currency}.NOK.SP?startPeriod={date}&endPeriod={date}"
		header = {"Accept": "application/vnd.sdmx.data+json;version=1.0.0-cts"}
		response = requests.get(entry_nb+url, headers=header)

		if response.status_code == 200:
			data = json.loads(response.content)
			out = data['dataSets'][0]['series']['0:0:0:0']['observations']['0'][0]
		elif response.status_code == 404:
			new_date = dateobj - datetime.timedelta(days=1)
			print("No matches. Trying previous day: " + new_date.isoformat())
			out = self.get_rate_from_bank(new_date.isoformat(), currency)
		else:
			print("Invalid request")
			print(response.status_code)
			print(response.content)
		return out