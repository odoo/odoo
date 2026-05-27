# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import json
import logging
import socket
import time
import uuid
from datetime import timedelta
from urllib.parse import urlparse

import requests

from odoo import fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ENDPOINTS = {
    'test': 'https://sandbox-openapi.baiwang.com/router/rest',
    'prod': 'https://openapi.baiwang.com/router/rest',
}


class BaiwangClient:
    """
    Baiwang Open API client for e-Fapiao integration.

    Handles authentication, request signing, and API calls following
    the Baiwang TOP-style protocol (validated against sandbox).
    """

    def __init__(self, company):
        self.company = company
        self.app_key = company.l10n_cn_baiwang_app_key
        self.app_secret = company.l10n_cn_baiwang_app_secret
        self.salt = company.l10n_cn_baiwang_salt
        self.username = company.l10n_cn_baiwang_username
        self.password = company.l10n_cn_baiwang_password
        self.tax_no = company.vat
        self.org_auth_code = company.l10n_cn_baiwang_org_auth_code
        mode = company.l10n_cn_edi_mode or 'test'
        self.endpoint = ENDPOINTS.get(mode, ENDPOINTS['test'])

    def _network_error(self, exc: Exception) -> UserError:
        return UserError(
            "Cannot reach Baiwang API endpoint (%s). Please check DNS/network access from the Odoo server.\n\nTechnical details: %s"
            % (self.endpoint, str(exc)),
        )

    def ensure_connection(self, timeout: float = 3.0):
        """Fail fast when Baiwang endpoint is unreachable (DNS/TCP)."""
        parsed_endpoint = urlparse(self.endpoint)
        hostname = parsed_endpoint.hostname
        if not hostname:
            raise UserError("Baiwang endpoint is not configured correctly: %s" % self.endpoint)
        port = parsed_endpoint.port or (443 if parsed_endpoint.scheme == 'https' else 80)

        try:
            socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
            with socket.create_connection((hostname, port), timeout=timeout):
                pass
        except OSError as exc:
            raise self._network_error(exc) from exc

    # ─── Hashing ────────────────────────────────────────────────────────

    @staticmethod
    def _md5(data: str) -> str:
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    @staticmethod
    def _sha256(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def _hash_password(self) -> str:
        """Hash password as: SHA256(password + salt)"""
        return self._sha256(self.password + self.salt)

    # ─── Signing ────────────────────────────────────────────────────────

    def _compute_sign(self, url_params: dict, body_str: str = '') -> str:
        """
        Baiwang TOP-style request signing.

        Formula: MD5(appSecret + sorted(key+value for non-empty url_params) + body_json_str + appSecret).upper()

        Args:
            url_params: URL query parameters (excluding 'sign' itself)
            body_str: The raw compact JSON body string
        """
        sorted_keys = sorted(url_params.keys())
        string_to_sign = self.app_secret

        for key in sorted_keys:
            value = url_params.get(key)
            if not key or value is None or (isinstance(value, str) and not value.strip()):
                continue
            string_to_sign += str(key) + str(value)

        string_to_sign += body_str
        string_to_sign += self.app_secret
        return self._md5(string_to_sign).upper()

    # ─── Token Management ───────────────────────────────────────────────

    def _get_token(self) -> str:
        """Get valid access token (cached or fresh)."""
        self.ensure_connection()

        if (self.company.l10n_cn_baiwang_cached_token
                and self.company.l10n_cn_baiwang_token_expiry
                and self.company.l10n_cn_baiwang_token_expiry > fields.Datetime.now()):
            return self.company.l10n_cn_baiwang_cached_token

        # Request new token via OAuth endpoint
        hashed_pw = self._hash_password()

        url_params = {
            'method': 'baiwang.oauth.token',
            'grant_type': 'password',
            'client_id': self.app_key,
            'version': '7.0',
            'timestamp': str(int(time.time() * 1000)),
            'signType': 'SHA256',
            'encryptType': 'NONE',
            'encryptScope': '00',
        }

        if self.org_auth_code:
            url_params['orgAuthCode'] = self.org_auth_code

        body = {
            'password': hashed_pw,
            'username': self.username,
            'client_secret': self.app_secret,
        }

        # Compute sign and add to URL params
        body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
        url_params['sign'] = self._compute_sign(url_params, body_str)

        response = None
        try:
            response = requests.post(
                self.endpoint,
                params=url_params,
                data=body_str.encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise self._network_error(exc) from exc
        result = response.json() if response else {}

        _logger.debug("Baiwang auth response: %s", result)

        if not result.get('success'):
            error_response = result.get('errorResponse', {})
            error_code = error_response.get('code', '')
            error_msg = error_response.get('message', 'Authentication failed')
            raise UserError(
                f"Baiwang authentication failed [{error_code}]: {error_msg}\n\n"
                "Please verify your App Key, App Secret, Username, Password, Salt, "
                "and Org Auth Code in Settings → Accounting → China Electronic Invoicing.",
            )

        token_data = result.get('response', {})
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 7200)

        self.company.sudo().write({
            'l10n_cn_baiwang_cached_token': access_token,
            'l10n_cn_baiwang_refresh_token': refresh_token,
            'l10n_cn_baiwang_token_expiry': fields.Datetime.now() + timedelta(seconds=expires_in - 300),
        })
        return access_token

    # ─── Raw HTTP Call ──────────────────────────────────────────────────

    def _raw_call(self, method: str, body: dict | None = None, version: str = '6.0', token: str | None = None):
        """
        Execute a raw API call to Baiwang.

        The request follows the validated pattern:
        - URL query params: method, version, appKey, format, timestamp, type, requestId, token, sign
        - For v7.0 APIs: also signType, encryptType, encryptScope
        - JSON body: compact format (no spaces), sent as raw bytes
        - Sign includes both URL params AND the raw body string
        """
        request_id = str(uuid.uuid4())

        url_params = {
            'method': method,
            'version': version,
            'appKey': self.app_key,
            'format': 'json',
            'timestamp': str(int(time.time() * 1000)),
            'type': 'sync',
            'requestId': request_id,
        }

        if token:
            url_params['token'] = token

        # v7.0 APIs require additional URL params
        if version == '7.0':
            url_params['signType'] = 'MD5'
            url_params['encryptType'] = 'NONE'
            url_params['encryptScope'] = '00'

        # Compact JSON body string (must match exactly what we send for signing)
        body = body or {}
        body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))

        # Compute signature over URL params + body string
        url_params['sign'] = self._compute_sign(url_params, body_str)

        # Send request with raw body bytes (not requests' json= which adds spaces)
        response = None
        try:
            response = requests.post(
                self.endpoint,
                params=url_params,
                data=body_str.encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'},
                timeout=15,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise self._network_error(exc) from exc
        return response.json() if response else {}

    # ─── Public API ─────────────────────────────────────────────────────

    def call_api(self, method: str, body: dict | None = None, version: str = '6.0'):
        """
        Public method for all business API calls (auto-handles token).

        Automatically retries once on token expiry errors (100001/100002).
        """
        self.ensure_connection()
        token = self._get_token()
        result = self._raw_call(method, body, version, token)

        # Auto-retry on token expiry
        error_code = str(result.get('errorResponse', {}).get('code', ''))
        if error_code in ('100001', '100002'):
            _logger.info("Baiwang token expired, refreshing...")
            self.company.sudo().write({
                'l10n_cn_baiwang_cached_token': False,
                'l10n_cn_baiwang_token_expiry': False,
            })
            token = self._get_token()
            result = self._raw_call(method, body, version, token)

        return result

    # ─── Convenience Methods ────────────────────────────────────────────

    def issue_invoice(self, invoice_data: dict):
        """
        Issue a blue or red invoice (v6.0 with data wrapper).

        Args:
            invoice_data: The invoice business content (goes inside 'data' key)
        """
        body = {
            'taxNo': self.tax_no,
            'data': invoice_data,
        }
        return self.call_api('baiwang.output.invoice.issue', body, version='6.0')

    def query_invoice(self, query_data: dict):
        """Query issued invoices."""
        body = {
            'taxNo': self.tax_no,
            'data': query_data,
        }
        return self.call_api('baiwang.output.invoice.query', body, version='6.0')

    def add_red_confirmation(self, red_form_data: dict):
        """
        Submit a red letter confirmation form (v7.0, flat body).

        Args:
            red_form_data: All red form fields (flat, top-level)
        """
        body = {'taxNo': self.tax_no}
        body.update(red_form_data)
        return self.call_api('baiwang.output.redinvoice.add', body, version='7.0')

    def operate_red_confirmation(self, red_confirm_uuid: str, red_confirm_no: str, confirm_type: str):
        """
        Operate on a red confirmation form (confirm/deny/revoke).

        Args:
            confirm_type: '01'=confirm, '02'=deny, '03'=revoke
        """
        body = {
            'taxNo': self.tax_no,
            'sellerTaxNo': self.tax_no,
            'redConfirmUuid': red_confirm_uuid,
            'redConfirmNo': red_confirm_no,
            'confirmType': confirm_type,
            'taxUserName': '',
        }
        return self.call_api('baiwang.output.redinvoice.operate', body, version='7.0')

    def query_red_form_list(self, filters: dict | None = None):
        """Query red confirmation form list (v7.0, flat body)."""
        body = {
            'taxNo': self.tax_no,
            'sellerTaxNo': self.tax_no,
            'buySelSelector': '0',
            'entryIdentity': '01',
            'pageNo': 1,
            'pageSize': 50,
            'queryAll': True,
        }
        if filters:
            body.update(filters)
        return self.call_api('baiwang.output.redinvoice.formlist', body, version='7.0')

    def query_red_form_detail(self, red_confirm_uuid: str):
        """Get red form detail (v6.0, flat body, no data wrapper)."""
        body = {
            'taxNo': self.tax_no,
            'sellerTaxNo': self.tax_no,
            'redConfirmUuid': red_confirm_uuid,
            'redConfirmNo': '',
            'taxUserName': '',
        }
        return self.call_api('baiwang.output.redinvoice.redforminfo', body, version='6.0')

    def query_terminals(self):
        """Query available invoicing terminals (v6.0, data wrapper)."""
        body = {
            'taxNo': self.tax_no,
            'data': {
                'invoiceTerminalCode': '',
                'invoiceTerminalName': '',
                'invoiceTypeCode': '',
                'machineNo': '',
                'taxDiskNo': '',
                'deviceType': '',
                'defaultInvoiceTypeCodes': '',
            },
        }
        return self.call_api('baiwang.output.terminal.query', body, version='6.0')
