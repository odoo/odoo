import logging
import uuid

import requests

_logger = logging.getLogger(__name__)


REQUEST_TIMEOUT = 10
MERCADO_PAGO_API_ENDPOINT = 'https://api.mercadopago.com'

# Not secret: identifies Odoo as the integrator so Mercado Pago can quantify
# the number of Odoo users on their backend. Sent in the order body under
# `integration_data` as documented by the Orders API.
MERCADO_PAGO_PLATFORM_ID = "dev_cdf1cfac242111ef9fdebe8d845d0987"


class MercadoPagoPosRequest:
    def __init__(self, mp_bearer_token):
        self.mercado_pago_bearer_token = mp_bearer_token

    def call_mercado_pago(self, method, endpoint, payload, idempotent=False):
        """ Make a request to Mercado Pago POS API.

        :param method: "GET", "POST", ...
        :param endpoint: The endpoint to be reached by the request.
        :param payload: The payload of the request.
        :param idempotent: When True, generate an X-Idempotency-Key header
            (required by the Orders API on POST /v1/orders and .../refund).
        :return The JSON-formatted content of the response.
        """
        endpoint = MERCADO_PAGO_API_ENDPOINT + endpoint
        header = {
            'Authorization': f"Bearer {self.mercado_pago_bearer_token}",
        }
        if idempotent:
            header['X-Idempotency-Key'] = str(uuid.uuid4())
        try:
            response = requests.request(method, endpoint, headers=header, json=payload, timeout=REQUEST_TIMEOUT)
            # Some endpoints (e.g. POST /v1/orders/{id}/events) return 204 with
            # no body; .json() would raise on empty content.
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as error:
            _logger.warning("Cannot connect with Mercado Pago POS. Error: %s", error)
            return {'errorMessage': str(error)}
        except ValueError as error:
            _logger.warning("Cannot decode response json. Error: %s", error)
            return {'errorMessage': f"Cannot decode Mercado Pago POS response. Error: {error}"}
