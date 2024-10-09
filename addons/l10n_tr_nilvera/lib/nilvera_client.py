from datetime import datetime
from pprint import pformat
import requests
import logging

from odoo import _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class NilveraClient:
    def __init__(self, environment=None, api_key=None, timeout_limit=None):
        self.is_production = environment and environment == 'production'
        self.base_url = 'https://api.nilvera.com' if self.is_production else 'https://apitest.nilvera.com'
        self.timeout_limit = timeout_limit

        self.client_header = {'Accept': 'application/json'}
        if api_key:
            self.client_header['Authorization'] = 'Bearer ' + api_key

    def request(self, method, endpoint, params=None, json=None, files=None, handle_response=True):
        start = str(datetime.utcnow())
        url = self.base_url + endpoint
        response = requests.request(
            method, url,
            headers=self.client_header,
            timeout=self.timeout_limit or 30,
            params=params,
            json=json,
            files=files
        )
        end = str(datetime.utcnow())
        _logger.info(
            "%s\nstart=%s\nend=%s\nargs=%s\nparams=%s\njson=%s\nresponse=%s" % (
                method, start, end, pformat(url), pformat(params), pformat(json), pformat(response)
            )
        )
        if handle_response:
            return self.handle_response(response)
        return response

    def handle_response(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            _logger.exception("HTTP error occurred: %s, Response content: %s" % (str(e), response.text or response.reason))
            if response.status_code == 401:
                raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more "
                                "rights or contact Nilvera."))
            else:
                raise UserError(_("Odoo could not perform this action at the moment, try again later."))
        except requests.exceptions.RequestException as e:
            _logger.exception("Request exception: %s" % str(e))
            raise UserError(_("An error occurred. Try again later."))

        try:
            return response.json()
        except ValueError:
            _logger.exception("Invalid JSON response: %s" % response.text)
            raise ValidationError(_("An error occurred. Try again later."))

    #   3947738924CDC8E0C42743DE362CE861407641E01C2A52802FEB4D32F59CEE2E    for first account test02
    #   0FD19CDF80E9177B70C5A08DCBADA458A7323A0C5DE3D5B5DB49B1175B60122F    for second account test02
