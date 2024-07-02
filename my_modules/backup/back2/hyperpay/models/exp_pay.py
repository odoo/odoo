import hashlib
import hmac
import logging
import pprint

import requests
from werkzeug.urls import url_join

from odoo import _, fields, models
from odoo.exceptions import ValidationError

try:
    from urllib.parse import urlencode
    from urllib.request import build_opener, Request, HTTPHandler
    from urllib.error import HTTPError, URLError
except ImportError:
    from urllib import urlencode
    from urllib2 import build_opener, Request, HTTPHandler, HTTPError, URLError
import json

_logger = logging.getLogger(__name__)

import uuid

# # Define a namespace UUID (can be any UUID)
# customer_id= str(59)
# namespace_uuid= uuid.uuid4()
# uid = uuid.uuid5(namespace_uuid, customer_id).hex
# print(f"UUID based on string '{customer_id}': {uid}")




class PaymentProvider():

    def request():
        url = "https://eu-test.oppwa.com/v1/checkouts"
        data = {
            'entityId': '8a8294174b7ecb28014b9699220015ca',
            'amount': '92.00',
            'currency': 'EUR',
            'paymentType': 'DB',
        }
        try:
            opener = build_opener(HTTPHandler)
            request = Request(url, data=urlencode(data).encode('utf-8'))
            request.add_header('Authorization', 'Bearer OGE4Mjk0MTc0YjdlY2IyODAxNGI5Njk5MjIwMDE1Y2N8c3k2S0pzVDg=')
            request.get_method = lambda: 'POST'
            response = opener.open(request)
            return json.loads(response.read())
        except HTTPError as e:
            return json.loads(e.read())
        except URLError as e:
            return e.reason

    def _hyperpay_make_request(method='POST'):
        """ Make a request to Hyperpay API at the specified endpoint.

        Note: self.ensure_one()

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        #310A0F769C504F03EB22E98C16942ED6.uat01-vm-tx01
        #7C4564832C208BF29A109A8914C11E10.uat01-vm-tx02

        url = "https://eu-test.oppwa.com/v1/checkouts"
        data = {
            'amount': 2300,
            'currency': 'USD',
            'entityId': '8a8294174b7ecb26304b9645126415ca',
            'paymentType': 'DB',
        }
        try:
            if method == 'GET':
                response = requests.get(url, params=urlencode(data).encode('utf-8'), headers={'Authorization': 'Bearer OGE4Mjk0MTc0YjdlY2IyODAxNGI5Njk5MjIwMDE1Y2N8c3k2S0pzVDg='}, timeout=10)
            else:
                response = requests.post(url, data=data, headers={'Authorization': 'Bearer OGE4Mjk0MTc0YjdlY2IyODAxNGI5Njk5MjIwMDE1Y2N8c3k2S0pzVDg='}, timeout=10)
            return response.json()
        except HTTPError as e:
            return json.loads(e.read())
        except URLError as e:
                return e.reason

    responseData = _hyperpay_make_request()
    #print(responseData)



