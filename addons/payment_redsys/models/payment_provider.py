# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64

import logging
import pprint

import requests
import xml.etree.ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import ValidationError

# from odoo.addons.payment_redsys import const
from odoo.addons.payment_redsys.controllers.main import RedsysController


from werkzeug import urls


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('redsys', 'Redsys')], ondelete={'redsys': 'set default'})
    redsys_merchant_code = fields.Char(string='Merchant Code', required_if_provider='redsys')

    def _redsys_get_api_url(self):
        if self.state == 'enabled':
            return 'https://sis.redsys.es/sis/realizarPago'
        else:  # 'test'
            return 'https://sis-t.redsys.es:25443/sis/realizarPago'

    def _redsys_make_request(self, payload=None, method='POST'):
        """
        Make a request to the Redsys API.
        :param payload: The payload to send in the request.
        :param method: The HTTP method to use (default is POST).
        :return: The response from the API.
        """

        # Parameters to send
        # Ds_MerchantParameters : Payment request data.
        # Ds_SignatureVersion : Version of the signature algorithm.
        # Ds_Signature : Signature of the payment request data.

        return_url = urls.url_join(self.provider_id.get_base_url(), RedsysController._return_url)

        # all parameters are of type string
        # the amount, is expressed in cents
        Ds_MerchantParameters = {
            "DS_MERCHANT_AMOUNT": "145",
            "DS_MERCHANT_CURRENCY": "978",
            "DS_MERCHANT_MERCHANTCODE": "999008881",
            "DS_MERCHANT_MERCHANTURL": "http://www.prueba.com/urlNotificacion.php",
            "DS_MERCHANT_ORDER": "1446068581",
            "DS_MERCHANT_TERMINAL": "1",
            "DS_MERCHANT_TRANSACTIONTYPE": "0",
            "DS_MERCHANT_URLKO": return_url,
            "DS_MERCHANT_URLOK": return_url,
        }
        json_Ds_MerchantParameters = json.dumps(Ds_MerchantParameters)
        encoded_Ds_MerchantParameters = base64.b64encode(json_Ds_MerchantParameters.encode()).decode()
        print("here--------------------")
        print(encoded_Ds_MerchantParameters)
        # it must be BASE64 encoded
        # The resulting string will be the value of the Ds_MerchantParameters parameter

        Ds_SignatureVersion = "HMAC_SHA256_V1"

        Ds_Signature = "signature"  # The signature of the payment request data
        # key 3DES with the key/code of the merchant and the order number
        # encoded_Ds_MerchantParameters
        # the 2 abobe together with HMAC_SHA256_V1 encryption then base64

        # If the request is made via cURL or using the Safari browser, the "+" symbols may be converted to spaces. To prevent this from happening, replace the "+" symbols with the equivalent "%2B" before sending the request.

        to_send = """
        <form name="from" action="https://sis-t.redsys.es:25443/sis/realizarPago" method="POST">
            <input type="hidden" name="Ds_SignatureVersion" value={Ds_SignatureVersion}/>
            <input type="hidden" name="Ds_MerchantParameters" value={encoded_Ds_MerchantParameters}}/>
            <input type="hidden" name="Ds_Signature" value={Ds_Signature}/>
        </form>
        """

        pass
