import logging
import requests

_logger = logging.getLogger(__name__)


def get_barcode_lookup_key(self):
    '''
    Get the Barcode Lookup API Key from the system.
    '''
    return self.env['ir.config_parameter'].sudo().get_param('product_barcodelookup.api_key', False)


def barcode_lookup_request(url, params={}):
    '''
    Make a request to the given URL and return the response.
    '''
    response = requests.get(url, params, timeout=15)
    if response.status_code != 200:
        _logger.warning('Status code: %s with the given URL: %s', response.status_code, url)
        # Used to authenticate api
        # When blank barcode request sent, returned status code 404 ensure the api is authenticated
        if response.status_code == 404:
            return {'authenticated': True, 'status_code': response.status_code}
        return {'status_code': response.status_code}
    return response
