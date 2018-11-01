import datetime
from decimal import Decimal
from json import loads as _loads

from requests import get as _get
from requests import post as _post
from requests.auth import HTTPBasicAuth

from exceptions import *

RELS = ['createGeneralJournalEntriesService', 'search']


class FikenError(Exception):
	"""
	Fange exceptions for invalide kommandoer og andre responser som
	ikke er en kode 200 respons.
	"""
	
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


class Fiken(object):
	def __init__(
			self,
			user=None,
			passwd=None,
			company_slug=None,
			timeout=180,
			parse_float=Decimal,
			parse_int=int,
			debug_endpoint=False):
		
		self.user = str(user) if user else None
		self.passwd = str(passwd) if passwd else None
		self.company_Slug = str(company_slug) if company_slug else None
		
		self.timeout = timeout
		self.parse_float = parse_float
		self.parse_int = parse_int
		self.debug_endpoint = debug_endpoint
		
		self.base_rel = 'https://fiken.no/api/v1/companies/'
		
		self.json_out = None
		self.current_year = datetime.datetime.now().year
	
	def action(self, command=None, body=None, year=None):
		if not self.user or not self.passwd:
			raise FikenError("Username and Password needed!")
		if command in RELS:
			url = self.base_rel + self.company_Slug + '/' + command
			
			if year:
				url = url + '/' + year
			
			if self.debug_endpoint:
				print("Current url is: {}".format(url))
				print("Current body is:")
				print(body)
			
			if body:
				header = {
					"Content-Type": "application/json",
					"Accept": "application/hal+json"}
				
				ret = _post(
					url=url,
					data=body,
					headers=header,
					auth=HTTPBasicAuth(self.user, self.passwd),
					timeout=self.timeout)
			else:
				ret = _get(url, auth=HTTPBasicAuth(self.user, self.passwd), timeout=self.timeout)
			
			if ret.status_code != 201:
				print(ret.content)
				raise FikenError(ret.status_code)

			if body:
				headers = ret.headers
				return headers
			else:
				self.json_out = _loads(ret.text, parse_float=self.parse_float, parse_int=self.parse_int)
				return self.json_out
		else:
			raise FikenError("Invalid command")
	
	def post_til_fiken(self, valid_json):
		return self.action(command="createGeneralJournalEntriesService", body=valid_json)


