# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import requests

from odoo import _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


def make_request(api_key, subdomain, version, endpoint, payload=None, method='POST'):
    """ Make a request to the Gelato API and return the JSON-formatted content of the response.

    :param str api_key: The Gelato API key used for signing requests.
    :param str subdomain: The subdomain of the Gelato API.
    :param str version: The version of the Gelato API.
    :param str endpoint: The API endpoint to call.
    :param dict payload: The payload of the request.
    :param str method: The HTTP method of the request.
    :return: The JSON-formatted content of the response.
    :rtype: dict
    """
    url = f'https://{subdomain}.gelatoapis.com/{version}/{endpoint}'
    headers = {
        'X-API-KEY': api_key or None
    }
    try:
        if method == 'GET':
            response = requests.get(url=url, params=payload, headers=headers, timeout=10)
        else:
            response = requests.post(url=url, json=payload, headers=headers, timeout=10)
        response_content = response.json()
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.exception("Invalid API request at %s with data %s", url, payload)
            raise UserError(response_content.get('message', ''))
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        _logger.exception("Unable to reach endpoint at %s", url)
        raise UserError(_("Could not establish the connection to the Gelato API."))
    return response.json()
