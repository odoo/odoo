import base64
import hashlib
import logging
import os
import time

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo.exceptions import UserError

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError


_logger = logging.getLogger(__name__)
TIMEOUT = 10


class KsefApiService:
    def __init__(self, company):
        self.company = company
        self.env = company.env
        self.mode = self.env['ir.config_parameter'].sudo().get_param('l10n_pl_edi_ksef.mode') or 'prod'
        self.refresh_token = company.l10n_pl_edi_refresh_token
        self.api_url = self._get_api_url()
        self.raw_symmetric_key = base64.b64decode(company.l10n_pl_edi_session_key) if company.l10n_pl_edi_session_key else None
        self.raw_iv = base64.b64decode(company.l10n_pl_edi_session_iv) if company.l10n_pl_edi_session_iv else None

    def _get_api_url(self):
        """Gets the correct KSeF API URL from the company's settings."""
        if self.mode == 'prod':
            return 'https://api.ksef.mf.gov.pl/v2'
        return 'https://api-test.ksef.mf.gov.pl/v2'

    def _make_headers(self, token):
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def _make_request(self, method, endpoint, is_auth_retry=False, **kwargs):
        """
        Helper method to make authenticated requests, handling token refresh on 401.
        :param method: 'GET' or 'POST'
        :param endpoint: The full URL for the request
        :param is_auth_retry: Flag to prevent infinite retry loops
        :param kwargs: Arguments for requests.session.request (e.g., json, headers, params, data, timeout)
        """
        kwargs.setdefault('headers', {})
        kwargs.setdefault('timeout', TIMEOUT)
        kwargs['headers'].update(self._make_headers(self.company.l10n_pl_edi_access_token))
        try:
            response = requests.request(method, endpoint, **kwargs)

            if response.status_code == 401 and not is_auth_retry:
                _logger.info("KSeF access token expired, refreshing...")
                self.refresh_access_token()
                # Pass is_auth_retry=True to prevent looping
                return self._make_request(method, endpoint, is_auth_retry=True, **kwargs)
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise KSeFRateLimitError("Too Many Requests", retry_after=retry_after)
            else:
                response.raise_for_status()
                return response

        except requests.exceptions.RequestException as e:
            error_text = e.response.text if e.response is not None else str(e)
            _logger.exception("KSeF API request failed: %s", error_text)
            raise UserError(self.env._("KSeF API Error: %s", error_text))

    def _get_public_keys(self):
        """
        Fetches the list of KSeF certificates and returns a dictionary containing
        both the Symmetric and Token encryption public keys.
        """
        endpoint = f"{self.api_url}/security/public-key-certificates"
        headers = {'Accept': 'application/json'}
        try:
            response = requests.get(endpoint, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            certs_data = response.json()

            public_keys = {
                'symmetric': None,
                'token': None,
            }

            for cert_info in certs_data:
                usage = cert_info.get('usage', [])

                if not set(usage) & {'SymmetricKeyEncryption', 'KsefTokenEncryption'}:
                    continue

                cert_b64 = cert_info['certificate']
                cert_der = base64.b64decode(cert_b64)
                cert = x509.load_der_x509_certificate(cert_der)
                public_key = cert.public_key()
                public_key_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode('utf-8')

                if 'SymmetricKeyEncryption' in usage:
                    public_keys['symmetric'] = public_key_pem
                if 'KsefTokenEncryption' in usage:
                    public_keys['token'] = public_key_pem

            if not public_keys['symmetric'] or not public_keys['token']:
                raise UserError(self.env._("Could not find all required KSeF public keys ('SymmetricKeyEncryption' and 'KsefTokenEncryption')."))
            return public_keys

        except requests.exceptions.RequestException as e:
            raise UserError(self.env._("Could not fetch KSeF public keys: %s", e.response.text if e.response else e))

    def open_ksef_session(self):
        """Builds the encrypted request and opens an interactive session, with one retry on token expiry."""
        if self.company.l10n_pl_edi_session_id and self.get_session_status().get('code') == 100:
            return
        self.raw_symmetric_key = os.urandom(32)
        self.raw_iv = os.urandom(16)
        ksef_public_key_pem = self._get_public_keys().get('symmetric')
        public_key = serialization.load_pem_public_key(ksef_public_key_pem.encode('utf-8'))
        encrypted_symmetric_key = public_key.encrypt(
            self.raw_symmetric_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        request_body = {
            "formCode": {"systemCode": "FA (3)", "schemaVersion": "1-0E", "value": "FA"},
            "encryption": {
                "encryptedSymmetricKey": base64.b64encode(encrypted_symmetric_key).decode('utf-8'),
                "initializationVector": base64.b64encode(self.raw_iv).decode('utf-8'),
            }
        }
        endpoint = f"{self.api_url}/sessions/online"
        headers = {'Content-Type': 'application/json'}

        try:
            response = self._make_request(
                'POST',
                endpoint,
                json=request_body,
                headers=headers
            )
            if 'error_message' in response:
                return response
            self.company.sudo().write({
                'l10n_pl_edi_session_id': response.json().get('referenceNumber'),
                'l10n_pl_edi_session_key': base64.b64encode(self.raw_symmetric_key),
                'l10n_pl_edi_session_iv': base64.b64encode(self.raw_iv),
            })
        except UserError as e:
            raise UserError(self.env._("Failed to open KSeF session: %s", e))

    def refresh_access_token(self):
        """Uses a refresh token to obtain a new access token and updates the service and company."""
        if not self.refresh_token:
            raise UserError(self.env._("No refresh token found to renew the session."))

        endpoint = f"{self.api_url}/auth/token/refresh"
        headers = self._make_headers(self.refresh_token)

        try:
            response = requests.post(endpoint, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            response_data = response.json()

            new_access_token = response_data.get('accessToken', {}).get('token')
            if not new_access_token:
                raise UserError(self.env._("Failed to retrieve a new access token from KSeF response."))

            self.company.l10n_pl_edi_access_token = new_access_token
            _logger.info("KSeF access token successfully refreshed.")
            return new_access_token

        except requests.exceptions.RequestException as e:
            error_text = e.response.text if e.response else str(e)
            _logger.exception("Failed to refresh KSeF access token: %s", error_text)
            raise UserError(self.env._("Failed to refresh KSeF access token. You may need to re-authenticate manually. Error: %s", error_text))

    def send_invoice(self, xml_content_bytes):
        """Encrypts a single invoice and sends it within an open session."""
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(xml_content_bytes) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.raw_symmetric_key), modes.CBC(self.raw_iv))
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        payload = {
            'invoiceHash': base64.b64encode(hashlib.sha256(xml_content_bytes).digest()).decode('utf-8'),
            'invoiceSize': len(xml_content_bytes),
            'encryptedInvoiceHash': base64.b64encode(hashlib.sha256(encrypted_data).digest()).decode('utf-8'),
            'encryptedInvoiceSize': len(encrypted_data),
            'encryptedInvoiceContent': base64.b64encode(encrypted_data).decode('utf-8'),
        }

        endpoint = f"{self.api_url}/sessions/online/{self.company.l10n_pl_edi_session_id}/invoices"
        headers = {'Content-Type': 'application/json'}

        response = self._make_request(
            'POST',
            endpoint,
            json=payload,
            headers=headers,
        )
        return response.json()

    def close_ksef_session(self):
        """Closes an interactive session."""
        if not self.company.l10n_pl_edi_session_id:
            _logger.warning("No KSeF session data found to close.")
            return

        endpoint = f"{self.api_url}/sessions/online/{self.company.l10n_pl_edi_session_id}/close"
        try:
            self._make_request('POST', endpoint)
            _logger.info("KSeF session closed gracefully")
        except UserError as e:
            _logger.warning("Failed to close KSeF session gracefully: %s", e)
        finally:
            self.company.sudo().write(dict.fromkeys([
                'l10n_pl_edi_session_id',
                'l10n_pl_edi_session_key',
                'l10n_pl_edi_session_iv',
            ], False))

    def get_session_status(self):
        if not self.company.l10n_pl_edi_session_id:
            raise UserError(self.env._("No active KSeF session found. Please open a session first."))
        endpoint = f"{self.api_url}/sessions/{self.company.l10n_pl_edi_session_id}"
        try:
            response = self._make_request('GET', endpoint)
            return response.json().get('status')
        except UserError as e:
            raise UserError(self.env._("Failed to check KSeF session: %s", e))

    def get_invoices_status(self, page_size=100, page_offset=0):
        """
        Gets the status of all invoices sent within the current session (paginated).
        Corresponds to: GET /api/v2/sessions/online/{referenceNumber}/invoices
        """
        if not self.company.l10n_pl_edi_session_id:
            raise UserError(self.env._("No active KSeF session found. Please open a session first."))

        endpoint = f"{self.api_url}/sessions/online/{self.company.l10n_pl_edi_session_id}/invoices"
        params = {'pageSize': page_size, 'pageOffset': page_offset}
        response = self._make_request('GET', endpoint, params=params)
        return response.json()

    def get_invoice_status(self, invoice_reference_number, session_id=None):
        """
        Gets the processing status of a specific invoice within the current session.
        :param invoice_reference_number: The 'invoiceReferenceNumber' returned by the send_invoice response.
        """
        session_id = session_id or self.company.l10n_pl_edi_session_id
        endpoint = f"{self.api_url}/sessions/{session_id}/invoices/{invoice_reference_number}"

        response = self._make_request('GET', endpoint)
        return response.json()

    def get_invoice_upo(self, invoice_reference_number, session_id=None):
        session_id = session_id or self.company.l10n_pl_edi_session_id
        endpoint = f"{self.api_url}/sessions/{session_id}/invoices/{invoice_reference_number}/upo"
        response = self._make_request('GET', endpoint)
        return response.content

    def get_challenge(self):
        """Fetches a one-time challenge from KSeF."""
        endpoint = f"{self.api_url}/auth/challenge"
        try:
            response = requests.post(endpoint, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(self.env._("Failed to get challenge code: %s", e.response.text if e.response else e))

    def authenticate_xades(self, signed_xml):
        """Sends a XAdES signed challenge to authenticate."""
        endpoint = f"{self.api_url}/auth/xades-signature"
        headers = {'Content-Type': 'application/xml;'}
        try:
            response = requests.post(endpoint, data=signed_xml.encode('utf-8'), headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(self.env._("Failed to authenticate with XAdES: %s", e.response.text if e.response else e))

    def authenticate_token(self, nip, challenge, encrypted_token_b64):
        """Starts authentication using a KSeF token."""
        endpoint = f"{self.api_url}/auth/ksef-token"
        payload = {
            "Challenge": challenge,
            "ContextIdentifier": {"Type": "Nip", "Value": nip},
            "EncryptedToken": encrypted_token_b64,
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(self.env._("Failed to start token authentication: %s", e.response.text if e.response else e))

    def check_auth_status(self, ref_number, temp_token):
        """Checks auth status with a retry loop for pending statuses."""
        endpoint = f"{self.api_url}/auth/{ref_number}"
        headers = self._make_headers(temp_token)

        for _attempt in range(5):
            try:
                response = requests.get(endpoint, headers=headers, timeout=TIMEOUT)
                response.raise_for_status()
                response_data = response.json()

                status_code = response_data.get('status', {}).get('code')
                status_description = response_data.get('status', {}).get('description')
                if status_code == 200:
                    return response_data
                elif status_code == 100:
                    time.sleep(2)
                    continue

                raise UserError(self.env._(
                    "KSeF Authentication failed with status %(status_code)s: %(status_description)s",
                    status_code=status_code,
                    status_description=status_description
                ))
            except requests.exceptions.RequestException as e:
                raise UserError(self.env._("Failed to check KSeF auth status: %s", e.response.text if e.response else e))

        raise UserError(self.env._("KSeF Authentication timed out. Please try again in a moment."))

    def redeem_token(self, temp_token):
        """Exchanges a temporary session token for permanent access/refresh tokens."""
        endpoint = f"{self.api_url}/auth/token/redeem"
        headers = {'Authorization': f'Bearer {temp_token}', 'Accept': 'application/json'}
        try:
            response = requests.post(endpoint, headers=headers, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(self.env._("Failed to redeem token: %s", e.response.text if e.response else e))

    def query_invoice_metadata(self, query_criteria, page_size=100, page_offset=0):
        endpoint = f"{self.api_url}/invoices/query/metadata"
        params = {'pageSize': page_size, 'pageOffset': page_offset}
        try:
            response = self._make_request('POST', endpoint, json=query_criteria, params=params)
            return response.json()
        except KSeFRateLimitError as e:
            return {'error': {'retry_after': e.retry_after, 'message': e.message}}

    def get_invoice_by_ksef_number(self, ksef_number):
        endpoint = f"{self.api_url}/invoices/ksef/{ksef_number}"
        try:
            response = self._make_request('GET', endpoint)
            return {'xml_content': response.content}
        except KSeFRateLimitError as e:
            return {'error': {'retry_after': e.retry_after, 'message': e.message}}
