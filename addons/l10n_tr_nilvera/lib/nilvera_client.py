import logging
import requests
from datetime import datetime
from json import JSONDecodeError

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def _get_nilvera_client(company, timeout_limit=None):
    return NilveraClient(
        environment=company.l10n_tr_nilvera_environment,
        api_key=company.l10n_tr_nilvera_api_key,
        timeout_limit=timeout_limit,
    )


class NilveraClient:
    def __init__(self, environment=None, api_key=None, timeout_limit=None):
        self.is_production = environment and environment == 'production'
        self.base_url = 'https://api.nilvera.com' if self.is_production else 'https://apitest.nilvera.com'
        self.timeout_limit = min(timeout_limit or 10, 30)

        self.__session = requests.Session()
        self.__session.headers.update({'Accept': 'application/json'})
        if api_key:
            self.__session.headers['Authorization'] = 'Bearer ' + api_key

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if hasattr(self, '_NilveraClient__session'):
            self.__session.close()

    def request(self, method, endpoint, params=None, json=None, files=None, handle_response=True):
        start = datetime.utcnow()
        url = self.base_url + endpoint

        try:
            response = self.__session.request(
                method, url,
                timeout=self.timeout_limit,
                params=params,
                json=json,
                files=files,
            )
        except requests.exceptions.RequestException as e:
            _logger.info("Network error during request: %s", e)
            raise UserError("Network connectivity issue. Please check your internet connection and try again.")

        end = datetime.utcnow()
        self._log_request(method, start, end, url, params, json, response)

        if handle_response:
            return self.handle_response(response)
        return response

    def _log_request(self, method, start, end, url, params, json, response):
        _logger.info(
            '"%(method)s %(url)s" %(status)s %(duration).3f',
            {
                'method': method,
                'url': url,
                'status': response.status_code,
                'duration': (end - start).total_seconds(),
            },
        )

    def handle_response(self, response):
        if response.status_code in {401, 403}:
            raise UserError("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera.")
        elif 403 < response.status_code < 600:
            raise UserError("Odoo could not perform this action at the moment, try again later.\n%s - %s" % (response.reason, response.status_code))

        try:
            return response.json()
        except JSONDecodeError:
            _logger.exception("Invalid JSON response: %s", response.text)
            raise UserError("An error occurred. Try again later.")
