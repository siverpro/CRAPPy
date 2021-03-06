# Built-in
import csv
import datetime
from decimal import Decimal
from json import loads as _loads

# 3rd party
from requests import get as _get
from requests import session

# Own
from exceptions import *

PRIVATE_COMMANDS = [
	'transactions',
	'capital_gains']


class BtcTaxError(Exception):
	def __init__(self, err):
		if err == 415:
			raise HTTP415
		elif err == 405:
			raise HTTP405
		elif err == 404:
			raise HTTP404
		elif err == 403:
			raise HTTP403
		elif err == 401:
			raise HTTP401
		elif err == 400:
			raise HTTP400

class BtcTax(object):
	def __init__(
			self,
			api_key=None,
			api_secret=None,
			fixer_api_key=None,
			username=None,
			password=None,
			timeout=5,
			parse_float=Decimal,
			parse_int=int,
			debug_endpoint=True,
			debug = False):
		
		self.api_key = str(api_key) if api_key else None
		self.api_secret = str(api_secret) if api_secret else None
		self.fixer_api_key = str(fixer_api_key) if fixer_api_key else None
		self.username = str(username) if username else None
		self.password = str(password) if password else None
		self.timeout = timeout
		self.parse_float = parse_float
		self.parse_int = parse_int
		self.debug_endpoint = debug_endpoint
		self.base_api_url = 'https://api.bitcoin.tax/v1/'
		self.base_login_url = 'https://bitcoin.tax/users/session'
		self.currency_base_url = 'http://data.fixer.io/api/'
		self.data = None
		self.filtered_data = None
		self.dict_list = []
		self.print = debug

	def read_csv_file(self, file):
		dict_list = []
		if self.print:
			print("Reading CSV file from Bitcoin.tax")
		try:
			reader = csv.DictReader(file.splitlines(), delimiter=",")
			for row in reader:
				if row["Symbol"] != "BTC":
					if "Unmatched" in row.keys():
						del row["Unmatched"]
					if None in row.keys():
						del row[None]
						
					dict_list.append(dict(row))
		except Exception as e:
			raise BtcTaxError(str(e))
		return dict_list

	def call(self, url=None, headers=None, payload=None, data=None):
		if payload is not None:
			ret = _get(url, headers=headers, timeout=self.timeout, params=payload)

			if ret.status_code != 200:
				raise BtcTaxError("Status Code: {}".format(ret.status_code))
			else:
				return ret

		elif data is not None:
			s = session()
			ret = s.post(url, data=data)
			if ret.status_code != 200:
				raise BtcTaxError("Status Code: %s" % ret.status_code)
			else:
				capital_gains_csv_url = 'https://bitcoin.tax/gains/' \
										'download?reporttype=allocations&format=csv&ignorezero=false&rounded=false'
				r = s.get(capital_gains_csv_url)
				encoding = r.headers['Content-Type'].split(";")[1].split("=")[1]
				return r.content.decode(str(encoding))

	def get_capital_gains(self):
		if not self.username or not self.password:
			raise BtcTaxError("Username and password needed")

		ret = None
		url = self.base_login_url
		form = {
			"email": self.username,
			"password": self.password,
			"continue": "",
			"code": ""}

		ret = self.call(url=url, data=form)

		capital_gains_csv = self.read_csv_file(ret)

		# We only want rows from the day before yesterday due to btctax calculations
		to_date = datetime.date.today() - datetime.timedelta(days=1)

		tx_list = []
		sales_list = []
		# Vars for summing up sales
		sale_date = None
		sale_sum = 0
		gain_sum = 0
		cost_basis_sum = 0
		sale_crypto_sum = 0
		currency = None

		symbols = []
		for row in capital_gains_csv:
			if row["Symbol"] not in symbols:
				symbols.append(row["Symbol"])

		for symbol in symbols:
			for row in capital_gains_csv:
				date_acquired = datetime.datetime.strptime(row['Date Acquired'], '%Y-%m-%d').date()
				date_sold = datetime.datetime.strptime(row['Date Sold'], '%Y-%m-%d').date()

				if date_acquired < to_date:
					tx_list.append(row)
				if row['Date Sold'] and (date_sold < to_date):
					if row['Date Sold'] != sale_date:  # A new date is encountered.

						# Add the old values to the list first
						if sale_date:
							sales_list.append({
								'Date Sold': sale_date,
								'Proceeds': sale_sum,
								'Cost Basis': cost_basis_sum,
								'Gain': gain_sum,
								'Symbol': symbol,
								'Volume': sale_crypto_sum,
								'Currency': row["Currency"]})

						# Reset vars
						sale_date = row['Date Sold']
						sale_sum = Decimal(row['Proceeds'])
						cost_basis_sum = Decimal(row["Cost Basis"])
						gain_sum = Decimal(row['Gain'])
						sale_crypto_sum = Decimal(row['Volume'])
						currency = row["Currency"]
					else:  # Just adding to the same date ...
						sale_sum += Decimal(row['Proceeds'])
						cost_basis_sum += Decimal(row["Cost Basis"])
						gain_sum += Decimal(row['Gain'])
						sale_crypto_sum += Decimal(row['Volume'])
			sales_list.append({
				'Date Sold': sale_date,
				'Proceeds': sale_sum,
				'Cost Basis': cost_basis_sum,
				'Gain': gain_sum,
				'Symbol': symbol,
				'Volume': sale_crypto_sum,
				'Currency': currency})

		return {"income": tx_list, "sales": sales_list}

	def get_transactions(self, taxyear=datetime.date.today().year, start=0, limit=None):
		if not self.api_key or not self.api_secret:
			raise BtcTaxError("Key and Secret needed!")
		url = self.base_api_url + '{}?'.format("transactions")

		headers = {
			'X-APIKEY': self.api_key,
			'X-APISECRET': self.api_secret,
			'Accept': 'application/json',
			'User-Agent': 'My user agent'}

		payload = {
			"taxyear": int(taxyear),
			"start": int(start),
			"limit": int(limit)}

		ret = self.call(url, headers, payload)

		json_out = _loads(ret.text, parse_float=self.parse_float, parse_int=self.parse_int)

		if json_out['status'] == 'success':
			return json_out['data']
		else:
			return None

