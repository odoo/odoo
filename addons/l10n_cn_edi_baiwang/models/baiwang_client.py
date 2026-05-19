# models/baiwang_client.py
import hashlib
import json
import time
import uuid
from datetime import timedelta

import requests

from odoo import fields
from odoo.exceptions import UserError


class BaiwangClient:
    def __init__(self, company):
        """ Initialize directly with the Odoo company record """
        self.company = company
        self.app_key = company.l10n_cn_baiwang_app_key
        self.app_secret = company.l10n_cn_baiwang_app_secret
        self.salt = company.l10n_cn_baiwang_salt
        self.url = "https://www-pre.baiwang.com"
        self.version = "6.0"

    def _get_valid_token(self):
        """ JIT Token Evaluation: Returns cached token or fetches a new one """
        # 1. Check if we have a valid cached token
        if self.company.l10n_cn_baiwang_cached_token and self.company.l10n_cn_baiwang_token_expiry:
            if self.company.l10n_cn_baiwang_token_expiry > fields.Datetime.now():
                return self.company.l10n_cn_baiwang_cached_token

        # 2. Token is expired/missing, fetch a new one
        payload = {"appKey": self.app_key, "appSecret": self.app_secret}

        # (Call the API directly here without a token parameter to get the token)
        # Note: You'll need to adapt the exact endpoint based on Baiwang's OAuth docs
        response = self._raw_api_call("baiwang.oauth.token", payload, token=None)

        if response.get("success"):
            new_token = response.get("response", {}).get("token")
            new_expiry = fields.Datetime.now() + timedelta(hours=23)

            # Save to Odoo database
            self.company.write({
                'l10n_cn_baiwang_cached_token': new_token,
                'l10n_cn_baiwang_token_expiry': new_expiry,
            })
            self.company.env.cr.commit()  # Prevent transaction locks

            return new_token
        msg = "Failed to authenticate with Baiwang API."
        raise UserError(msg)

    def _raw_api_call(self, method, data_dict, token):
        """ The actual HTTP request logic (what call_api used to be) """
        timestamp = str(int(time.time()))
        request_id = str(uuid.uuid4())

        payload_str = json.dumps(data_dict)
        raw_str = f"{self.app_key}{payload_str}{self.salt}"
        sign = hashlib.md5(raw_str.encode('utf-8')).hexdigest().upper()

        params = {
            "method": method, "version": self.version, "appKey": self.app_key,
            "format": "json", "timestamp": timestamp, "type": "sync",
            "requestId": request_id, "sign": sign,
        }
        if token:
            params["token"] = token

        endpoint = f"{self.url}/router/rest"
        response = requests.post(endpoint, params=params, json=data_dict, timeout=10)
        response.raise_for_status()
        return response.json()

    def call_api(self, method, data_dict):
        """ The public method Odoo models will use """
        token = self._get_valid_token()
        return self._raw_api_call(method, data_dict, token)
