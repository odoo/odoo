# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import pytz
import urllib.parse
import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


from odoo import _

PRODUCTION_URL = "https://einvoice.ecpay.com.tw/"
STAGING_URL = "https://einvoice-stage.ecpay.com.tw/"
TIMEOUT = 20


class EcPayAPI:
    def __init__(self, company_id, is_b2b=False):
        url = STAGING_URL if company_id.l10n_tw_edi_ecpay_staging_mode else PRODUCTION_URL
        self.request_url = url + ("B2BInvoice/" if is_b2b else "B2CInvoice/")
        self.merchant_id = company_id.sudo().l10n_tw_edi_ecpay_merchant_id
        self.hashkey = company_id.sudo().l10n_tw_edi_ecpay_hashkey
        self.hashIV = company_id.sudo().l10n_tw_edi_ecpay_hashIV

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
        ecpay_time = datetime.datetime.strptime(time_before, "%Y-%m-%d %H:%M:%S")
        ecpay_time = pytz.timezone('Asia/Taipei').localize(ecpay_time)
        return ecpay_time.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")

    def call_ecpay_api(self, endpoint, json_data):
        try:
            self.cipher = Cipher(algorithms.AES(self.hashkey.encode('utf-8')), modes.CBC(self.hashIV.encode('utf-8')))
            # urlencode the JSON string firstly and then do AES encryption
            urlencode_data = urllib.parse.quote(json.dumps(json_data))
            encrypted_data = self.encrypt(urlencode_data)
            json_body = {
                "MerchantID": self.merchant_id,
                "RqHeader": {
                    "Timestamp": round(datetime.datetime.now().timestamp())
                },
                "Data": base64.b64encode(encrypted_data).decode('utf-8')
            }
            response = requests.post(self.request_url + endpoint, json=json_body, timeout=TIMEOUT)
            response_json = response.json()
            if response.status_code != 200:
                return {
                    "RtnCode": 0,
                    "RtnMsg": _("ECPay API Error: %(error_message)s.", error_message=response_json.get("TransMsg")),
                }

            if not response_json.get("Data"):
                return {
                    "RtnCode": 0,
                    "RtnMsg": _("ECPay API Error: %(error_message)s, Error Code: %(error_code)s", error_message=response_json.get("TransMsg"), error_code=response_json.get("TransCode")),
                }
            # AES decryption to the Data firstly and then do urldecode
            decrypted_response_data = self.decrypt(response_json["Data"])
            unquoted_data = urllib.parse.unquote(decrypted_response_data)
            json_data = json.loads(unquoted_data)
        except ValueError as e:
            if "key" in str(e):
                error_message = _("ECPay API Error: Invalid Hashkey. Please check your ECPay configuration.")
            elif "IV" in str(e):
                error_message = _("ECPay API Error: Invalid HashIV. Please check your ECPay configuration.")
            else:
                error_message = _("ECPay API Error: %(error_message)s", error_message=str(e))
            return {
                "RtnCode": 0,
                "RtnMsg": error_message,
            }
        return json_data
