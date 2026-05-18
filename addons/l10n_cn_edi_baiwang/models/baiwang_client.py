import hashlib
import time
import uuid
import requests
import json
from odoo.exceptions import UserError

class BaiwangClient:
    def __init__(self, app_key, app_secret, salt, url="https://www-pre.baiwang.com"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.salt = salt
        self.url = url
        self.version = "6.0"

    def _generate_sign(self, payload_str):
        """
        MD5 Signature generation. 
        Note: Adjust the concatenation logic based on Baiwang's specific sign rules
        (usually appKey + payload + salt).
        """
        raw_str = f"{self.app_key}{payload_str}{self.salt}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest().upper()

    def call_api(self, method, data_dict, token):
        """Standardized method to call Baiwang REST APIs."""
        timestamp = str(int(time.time()))
        request_id = str(uuid.uuid4())

        payload_str = json.dumps(data_dict)
        sign = self._generate_sign(payload_str)

        # Public parameters required in the URL/Query
        params = {
            "method": method,
            "version": self.version,
            "appKey": self.app_key,
            "format": "json",
            "timestamp": timestamp,
            "type": "sync",
            "requestId": request_id,
            "sign": sign,
            "token": token
        }

        endpoint = f"{self.url}/router/rest"

        try:
            response = requests.post(endpoint, params=params, json=data_dict, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(f"Network error connecting to Baiwang: {str(e)}")
