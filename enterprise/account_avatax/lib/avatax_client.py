"""
AvaTax Software Development Kit for Python.

   Copyright 2019 Avalara, Inc.
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
@author     Robert Bronson
@author     Phil Werner
@author     Adrienne Karnoski
@author     Han Bao
@copyright  2019 Avalara, Inc.
@license    https://www.apache.org/licenses/LICENSE-2.0
@version    TBD
@link       https://github.com/avadev/AvaTax-REST-V2-Python-SDK
"""
# This is a stripped down version of the upstream Avatax library for Odoo. Changes were made to
# prevent arbitrary requests in case function references get leaked.

from requests.auth import HTTPBasicAuth
from datetime import datetime
from pprint import pformat
import requests
import logging

str_type = (str, type(None))
_logger = logging.getLogger(__name__)


class AvataxClient:
    def __init__(self, app_name=None, app_version=None, machine_name=None,
                 environment=None, timeout_limit=None):
        if not all(isinstance(i, str_type) for i in [app_name,
                                                     machine_name,
                                                     environment]):
            raise ValueError('Input(s) must be string or none type object')
        self.base_url = 'https://sandbox-rest.avatax.com'
        self.is_production = environment and environment.lower() == 'production'
        if self.is_production:
            self.base_url = 'https://rest.avatax.com'
        self.auth = None
        self.app_name = app_name
        self.app_version = app_version
        self.machine_name = machine_name
        self.client_id = '{}; {}; Python SDK; 18.5; {};'.format(app_name,
                                                                app_version,
                                                                machine_name)
        self.client_header = {'X-Avalara-Client': self.client_id}
        self.timeout_limit = timeout_limit

    def add_credentials(self, username=None, password=None):
        if not all(isinstance(i, str_type) for i in [username, password]):
            raise ValueError('Input(s) must be string or none type object')
        if username and not password:
            self.client_header['Authorization'] = 'Bearer ' + username
        else:
            self.auth = HTTPBasicAuth(username, password)
        return self

    def request(self, method, endpoint, params, json):
        """Allow to enable a trace of requests in the logger."""
        start = str(datetime.utcnow())
        url = '{}/api/v2/{}'.format(self.base_url, endpoint)
        response = requests.request(
            method, url,
            auth=self.auth,
            headers=self.client_header,
            timeout=self.timeout_limit if self.timeout_limit else 1200,
            params=params,
            json=json
        ).json()
        end = str(datetime.utcnow())
        if hasattr(self, 'logger'):
            self.logger(
                f"{method}\nstart={start}\nend={end}\nargs={pformat(url)}\nparams={pformat(params)}\njson={pformat(json)}\n"
                f"response={pformat(response)}"
            )
        return response

    def create_transaction(self, model, include=None):
        return self.request('POST', 'transactions/createoradjust', params=include, json={'createTransactionModel': model})

    def uncommit_transaction(self, companyCode, transactionCode, include=None):
        return self.request('POST', 'companies/{}/transactions/{}/uncommit'.format(companyCode, transactionCode),
                            params=include, json=None)

    def void_transaction(self, companyCode, transactionCode, model, include=None):
        return self.request('POST', 'companies/{}/transactions/{}/void'.format(companyCode, transactionCode),
                            params=include, json=model)

    def ping(self):
        return self.request('GET', 'utilities/ping', params=None, json=None)

    def resolve_address(self, model=None):
        return self.request('POST', 'addresses/resolve', params=None, json=model)

    def list_entity_use_codes(self, include=None):
        return self.request('GET', 'definitions/entityusecodes', params=include, json=None)
