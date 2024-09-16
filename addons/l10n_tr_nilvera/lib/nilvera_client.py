import logging
import requests
from datetime import datetime
from json import JSONDecodeError
from pprint import pformat

from odoo import _
from odoo.exceptions import UserError, ValidationError

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

        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
        if api_key:
            self.session.headers.update({'Authorization': 'Bearer ' + api_key})

    def request(self, method, endpoint, params=None, json=None, files=None, handle_response=True):
        start = str(datetime.utcnow())
        url = self.base_url + endpoint

        response = self.session.request(
            method, url,
            timeout=self.timeout_limit,
            params=params,
            json=json,
            files=files,
        )
        end = str(datetime.utcnow())
        self._log_request(method, start, end, url, params, json, response)

        if handle_response:
            return self.handle_response(response)
        return response

    def _log_request(self, method, start, end, url, params, json, response):
        _logger.info(
            "%(method)s\nstart=%(start)s\nend=%(end)s\nurl=%(url)s\nparams=%(params)s\njson=%(json)s\nresponse=%(response)s",
            {
                "method": method,
                "start": start,
                "end": end,
                "url": pformat(url),
                "params": pformat(params),
                "json": pformat(json),
                "response": pformat(response),
            },
        )

    def handle_response(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.exception("HTTP error occurred")
            if response.status_code in {401, 403}:
                raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."))
            else:
                raise UserError(_("Odoo could not perform this action at the moment, try again later."))
        except requests.exceptions.RequestException:
            _logger.exception("Request exception occurred")
            raise UserError(_("An error occurred. Try again later."))

        try:
            return response.json()
        except JSONDecodeError:
            _logger.exception("Invalid JSON response: %s", response.text)
            raise ValidationError(_("An error occurred. Try again later."))

    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
