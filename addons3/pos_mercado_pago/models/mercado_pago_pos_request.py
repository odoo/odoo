import logging
import requests

_logger = logging.getLogger(__name__)


REQUEST_TIMEOUT = 10
MERCADO_PAGO_API_ENDPOINT = 'https://api.mercadopago.com'


class MercadoPagoPosRequest:
    def __init__(self, mp_bearer_token):
        self.mercado_pago_bearer_token = mp_bearer_token

    def call_mercado_pago(self, method, endpoint, payload):
        """ Make a request to Mercado Pago POS API.

        :param method: "GET", "POST", ...
        :param endpoint: The endpoint to be reached by the request.
        :param payload: The payload of the request.
        :return The JSON-formatted content of the response.
        """
        endpoint = MERCADO_PAGO_API_ENDPOINT + endpoint
        header = {'Authorization': f"Bearer {self.mercado_pago_bearer_token}"}
        try:
            response = requests.request(method, endpoint, headers=header, json=payload, timeout=REQUEST_TIMEOUT)
            return response.json()
        except requests.exceptions.RequestException as error:
            _logger.warning("Cannot connect with Mercado Pago POS. Error: %s", error)
            return {'errorMessage': str(error)}
        except ValueError as error:
            _logger.warning("Cannot decode response json. Error: %s", error)
            return {'errorMessage': f"Cannot decode Mercado Pago POS response. Error: {error}"}
