# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import pytz
import urllib.parse
import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


PRODUCTION_URL = "https://einvoice.ecpay.com.tw/"
STAGING_URL = "https://einvoice-stage.ecpay.com.tw/"
TIMEOUT = 20


def transfer_time(time_before):
    ecpay_time = datetime.datetime.strptime(time_before, "%Y-%m-%d %H:%M:%S")
    ecpay_time = pytz.timezone('Asia/Taipei').localize(ecpay_time)
    return ecpay_time.astimezone(pytz.UTC).strftime("%Y-%m-%d %H:%M:%S")


def convert_utc_time_to_tw_time(utc_datetime):
    """
        Converts UTC datetime object to a TW date string.

        :param utc_datetime: datetime.datetime(2026, 1, 23, 18, 0, 0)
        :return: "2026-01-24"
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)

    tw_tz = pytz.timezone('Asia/Taipei')
    tw_time = utc_datetime.astimezone(tw_tz)

    return tw_time.strftime("%Y-%m-%d")


def encrypt(data, cipher):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data.encode("utf-8")) + padder.finalize()
    encryptor = cipher.encryptor()
    return encryptor.update(padded_data) + encryptor.finalize()


def decrypt(data, cipher):
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(base64.b64decode(data)) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(decrypted_data) + unpadder.finalize()


def call_ecpay_api(endpoint, json_data, company_id, is_b2b=False):
    """
    Function for interacting with the ECPay e-invoice API.

    This function provides a structured way to configure and prepare requests
    for ECPay's B2B or B2C invoice services

    AES-CBC encryption is used for hashashkey and hashIV:
    https://developers.ecpay.com.tw/?p=22160
    """
    url = STAGING_URL if company_id.l10n_tw_edi_ecpay_staging_mode else PRODUCTION_URL
    request_url = url + ("B2BInvoice" if is_b2b else "B2CInvoice")
    hashkey = company_id.sudo().l10n_tw_edi_ecpay_hashkey
    hashIV = company_id.sudo().l10n_tw_edi_ecpay_hashIV
    try:
        cipher = Cipher(algorithms.AES(hashkey.encode('utf-8')), modes.CBC(hashIV.encode('utf-8')))
        # Encode the JSON string firstly then do AES encryption
        urlencode_data = urllib.parse.quote(json.dumps(json_data))
        encrypted_data = encrypt(urlencode_data, cipher)
        json_body = {
            "MerchantID": company_id.sudo().l10n_tw_edi_ecpay_merchant_id,
            "RqHeader": {
                "Timestamp": round(datetime.datetime.now().timestamp()),
            },
            "Data": base64.b64encode(encrypted_data).decode('utf-8'),
        }
        response = requests.post(request_url + endpoint, json=json_body, timeout=TIMEOUT)
        response_json = response.json()
        if response.status_code != 200:
            return {
                "RtnCode": 0,
                "RtnMsg": company_id.env._("ECPay API Error: %(error_message)s.", error_message=response_json.get("TransMsg")),
            }

        if not response_json.get("Data"):
            return {
                "RtnCode": 0,
                "RtnMsg": company_id.env._("ECPay API Error: %(error_message)s, Error Code: %(error_code)s", error_message=response_json.get("TransMsg"), error_code=response_json.get("TransCode")),
            }
        # AES decryption to the Data firstly then decode
        decrypted_response_data = decrypt(response_json["Data"], cipher)
        unquoted_data = urllib.parse.unquote(decrypted_response_data)
        json_data = json.loads(unquoted_data)
    except ValueError as e:
        if "key" in str(e):
            error_message = company_id.env._("ECPay API Error: Invalid Hashkey. Please check your ECPay configuration.")
        elif "IV" in str(e):
            error_message = company_id.env._("ECPay API Error: Invalid HashIV. Please check your ECPay configuration.")
        else:
            error_message = company_id.env._("ECPay API Error: %(error_message)s", error_message=str(e))
        return {
            "RtnCode": 0,
            "RtnMsg": error_message,
        }
    return json_data
