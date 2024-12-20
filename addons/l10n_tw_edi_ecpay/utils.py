import datetime
import urllib.parse
import requests
import json
import base64

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from odoo.exceptions import UserError
from odoo import _


class EcPayAPI():
    def __init__(self, key, iv, merchant_id):
        self.merchant_id = merchant_id
        self.cipher = Cipher(algorithms.AES(key.encode('utf-8')), modes.CBC(iv.encode('utf-8')))

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

    def call_ecpay_api(self, request_url, json_data):
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
        response = requests.post(request_url, json=json_body, timeout=100)
        response_json = response.json()
        if response_json["Data"] is None:
            raise UserError(_("ECPay API Error: Cannot get reponse data from ECpay."))
        # AES decryption to the Data firstly and then do urldecode
        decrypted_response_data = self.decrypt(response_json["Data"])
        unquoted_data = urllib.parse.unquote(decrypted_response_data)
        json_data = json.loads(unquoted_data)
        return json_data
