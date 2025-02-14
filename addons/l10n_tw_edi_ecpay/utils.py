# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import urllib.parse

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import _
from odoo.exceptions import UserError

PRODUCTION_URL = "https://einvoice.ecpay.com.tw/B2CInvoice/"
STAGING_URL = "https://einvoice-stage.ecpay.com.tw/B2CInvoice/"
TIMEOUT = 20


class EcPayAPI():
    def __init__(self, company_id):
        self.request_url = STAGING_URL if company_id.l10n_tw_edi_ecpay_staging_mode else PRODUCTION_URL
        self.merchant_id = company_id.l10n_tw_edi_ecpay_merchant_id
        self.hashkey = company_id.l10n_tw_edi_ecpay_hashkey
        self.hashIV = company_id.l10n_tw_edi_ecpay_hashIV
        self.cipher = Cipher(algorithms.AES(self.hashkey.encode('utf-8')), modes.CBC(self.hashIV.encode('utf-8')))

    def encrypt(self, data):
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode("utf-8")) + padder.finalize()
        encryptor = self.cipher.encryptor()
        return encryptor.update(padded_data) + encryptor.finalize()

    def decrypt(self, data):
        decryptor = self.cipher.decryptor()
        decrypted_data = decryptor.update(base64.b64decode(data)) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decrypted_data) + unpadder.finalize()

    def _transfer_time(self, time_before):
        """Transfer the time from GMT+8 (from Ecpay API) to UTC"""
        time_after = (
            datetime.datetime.strptime(time_before, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=8)
        ).strftime("%Y-%m-%d %H:%M:%S")
        return time_after

    def call_ecpay_api(self, endpoint, json_data):
        # urlencode the JSON string firstly and then do AES encryption
        urlencode_data = urllib.parse.quote(json.dumps(json_data))
        encrypted_data = self.encrypt(urlencode_data)
        json_body = {
            "MerchantID": self.merchant_id,
            "RqHeader": {
                "Timestamp": int(round(datetime.datetime.now().timestamp()))
            },
            "Data": base64.b64encode(encrypted_data).decode('utf-8')
        }
        response = requests.post(self.request_url + endpoint, json=json_body, timeout=TIMEOUT)
        response_json = response.json()
        if not response_json.get("Data"):
            raise UserError(_("ECPay API Error: %(error_message)s, Error Code: %(error_code)s", error_message=response_json.get("TransMsg"), error_code=response_json.get("TransCode")))
        # AES decryption to the Data firstly and then do urldecode
        decrypted_response_data = self.decrypt(response_json["Data"])
        unquoted_data = urllib.parse.unquote(decrypted_response_data)
        json_data = json.loads(unquoted_data)
        return json_data
