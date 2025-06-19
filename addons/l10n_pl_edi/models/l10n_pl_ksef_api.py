import base64
import os
from datetime import time
import hashlib
import logging
import requests
from odoo import _
from odoo.exceptions import UserError
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

_logger = logging.getLogger(__name__)


class KsefApiService:
    def __init__(self, company):
        self.company = company
        self.access_token = company.l10n_pl_access_token
        self.refresh_token = company.l10n_pl_refresh_token
        self.api_url = self._get_api_url()
        self.session = requests.Session()
        self.session_data = None
        self.raw_symmetric_key = None

    def _get_api_url(self):
        """Gets the correct KSeF API URL from the company's settings."""
        mode = self.company.l10n_pl_edi_mode
        if mode == 'prod':
            return 'https://ksef.mf.gov.pl/api/v2'
        return 'https://ksef-test.mf.gov.pl/api/v2'

    def _get_public_keys(self):
        """
        Fetches the list of KSeF certificates and returns a dictionary containing
        both the Symmetric and Token encryption public keys.
        """
        endpoint = f"{self.api_url}/security/public-key-certificates"
        headers = {'Accept': 'application/json'}
        try:
            response = self.session.get(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            certs_data = response.json()

            public_keys = {
                'symmetric': None,
                'token': None,
            }

            for cert_info in certs_data:
                usage = cert_info.get('usage', [])

                if not any(u in usage for u in ['SymmetricKeyEncryption', 'KsefTokenEncryption']):
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
                raise UserError(_("Could not find all required KSeF public keys ('SymmetricKeyEncryption' and 'KsefTokenEncryption')."))

            return public_keys

        except requests.exceptions.RequestException as e:
            raise UserError(_("Could not fetch KSeF public keys: %s", e.response.text if e.response else e))

    def open_ksef_session(self):
        """Builds the encrypted request and opens an interactive session, with one retry on token expiry."""
        self.raw_symmetric_key = os.urandom(32)
        raw_iv = os.urandom(16)
        ksef_public_key_pem = self._get_public_keys().get('symmetric')
        public_key = serialization.load_pem_public_key(ksef_public_key_pem.encode('utf-8'))
        encrypted_symmetric_key = public_key.encrypt(
            self.raw_symmetric_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        request_body = {
            "formCode": {"systemCode": "FA (2)", "schemaVersion": "1-0E", "value": "FA"},
            "encryption": {
                "encryptedSymmetricKey": base64.b64encode(encrypted_symmetric_key).decode('utf-8'),
                "initializationVector": base64.b64encode(raw_iv).decode('utf-8'),
            }
        }
        endpoint = f"{self.api_url}/sessions/online"
        headers = {'Authorization': f'Bearer {self.access_token}', 'Accept': 'application/json', 'Content-Type': 'application/json'}

        try:
            response = self.session.post(endpoint, json=request_body, headers=headers, timeout=10)
            if response.status_code == 401:
                _logger.info("KSeF access token expired, refreshing...")
                self.refresh_access_token()
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = self.session.post(endpoint, json=request_body, headers=headers, timeout=10)

            response.raise_for_status()
            self.session_data = response.json()

        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to open KSeF session: %s", e.response.text if e.response else e))

    def refresh_access_token(self):
        """Uses a refresh token to obtain a new access token and updates the service and company."""
        if not self.refresh_token:
            raise UserError(_("No refresh token found to renew the session."))

        endpoint = f"{self.api_url}/auth/token/refresh"
        headers = {'Authorization': f'Bearer {self.refresh_token}', 'Accept': 'application/json'}

        try:
            response = self.session.post(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            response_data = response.json()

            new_access_token = response_data.get('accessToken', {}).get('token')
            if not new_access_token:
                raise UserError(_("Failed to retrieve a new access token from KSeF response."))

            self.access_token = new_access_token

            self.company.write({
                'l10n_pl_access_token': new_access_token,
            })
            return new_access_token

        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to refresh KSeF access token: %s", e.response.text if e.response else e))

    def send_invoice(self, xml_content_bytes):
        """Encrypts a single invoice and sends it within an open session."""
        iv = os.urandom(16)
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(xml_content_bytes) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.raw_symmetric_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        encrypted_content_bytes = iv + encrypted_data

        payload = {
            'invoiceHash': base64.b64encode(hashlib.sha256(xml_content_bytes).digest()).decode('utf-8'),
            'invoiceSize': len(xml_content_bytes),
            'encryptedInvoiceHash': base64.b64encode(hashlib.sha256(encrypted_content_bytes).digest()).decode('utf-8'),
            'encryptedInvoiceSize': len(encrypted_content_bytes),
            'encryptedInvoiceContent': base64.b64encode(encrypted_content_bytes).decode('utf-8'),
        }

        endpoint = f"{self.api_url}/sessions/online/{self.session_data.get('referenceNumber')}/invoices"
        headers = {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}
        response = self.session.post(endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def close_ksef_session(self):
        """Closes an interactive session."""
        endpoint = f"{self.api_url}/sessions/online/{self.session_data.get('referenceNumber')}/close"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            self.session.post(endpoint, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            _logger.warning("Failed to close KSeF session gracefully: %s", e)

    def get_challenge(self):
        """Fetches a one-time challenge from KSeF."""
        endpoint = f"{self.api_url}/auth/challenge"
        try:
            response = self.session.post(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to get challenge code: %s", e.response.text if e.response else e))

    def authenticate_xades(self, signed_xml):
        """Sends a XAdES signed challenge to authenticate."""
        endpoint = f"{self.api_url}/auth/xades-signature"
        headers = {'Content-Type': 'application/xml;'}
        try:
            response = self.session.post(endpoint, data=signed_xml.encode('utf-8'), headers=headers, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to authenticate with XAdES: %s", e.response.text if e.response else e))

    def authenticate_token(self, nip, challenge, encrypted_token_b64):
        """Starts authentication using a KSeF token."""
        endpoint = f"{self.api_url}/auth/ksef-token"
        payload = {
            "Challenge": challenge,
            "ContextIdentifier": {"Type": "Nip", "Value": nip},
            "EncryptedToken": encrypted_token_b64,
        }
        try:
            response = self.session.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to start token authentication: %s", e.response.text if e.response else e))

    def check_auth_status(self, ref_number, temp_token):
        """Checks auth status with a retry loop for pending statuses."""
        endpoint = f"{self.api_url}/auth/{ref_number}"
        headers = {'Authorization': f'Bearer {temp_token}', 'Accept': 'application/json'}

        # Retry up to 5 times, waiting 2 seconds between each attempt
        for attempt in range(5):
            try:
                response = self.session.get(endpoint, headers=headers, timeout=10)
                response.raise_for_status()
                response_data = response.json()

                status_code = response_data.get('status', {}).get('code')
                status_description = response_data.get('status', {}).get('description')

                if status_code == 200:
                    return response_data

                if status_code == 100:  # Status "In Progress"
                    _logger.info("KSeF auth status is 'In Progress', retrying...")
                    time.sleep(2)
                    continue

                raise UserError(_(
                    "KSeF Authentication failed with status %(status_code)s: %(status_description)s",
                    status_code=status_code,
                    status_description=status_description
                ))
            except requests.exceptions.RequestException as e:
                raise UserError(_("Failed to check KSeF auth status: %s", e.response.text if e.response else e))

        # If the loop finishes without success, raise a timeout error
        raise UserError(_("KSeF Authentication timed out. Please try again in a moment."))

    def redeem_token(self, temp_token):
        """Exchanges a temporary session token for permanent access/refresh tokens."""
        endpoint = f"{self.api_url}/auth/token/redeem"
        headers = {'Authorization': f'Bearer {temp_token}', 'Accept': 'application/json'}
        try:
            response = self.session.post(endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to redeem token: %s", e.response.text if e.response else e))
