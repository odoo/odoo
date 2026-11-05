import base64
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import Command
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService

_logger = logging.getLogger(__name__)

ROLES = {
    'seller': 'Subject1',
    'buyer': 'Subject2',
    'third_party': 'Subject3',
    'authorized': 'SubjectAuthorized',
}


class KsefApiServiceBatch(KsefApiService):
    @staticmethod
    def b64(value):
        if not value:
            return False
        if isinstance(value, str):
            value = value.encode()
        return base64.b64encode(value).decode()

    @staticmethod
    def u64(value):
        if not value:
            return False
        if isinstance(value, str):
            value = value.encode()
        return base64.b64decode(value)

    @staticmethod
    def pretty_json(value):
        return json.dumps(value, indent=4)

    @staticmethod
    def _url_to_name(url):
        return Path(unquote(urlparse(url).path)).name

    def _create_encryption_data(self):
        raw_symmetric_key = os.urandom(32)
        raw_iv = os.urandom(16)
        ksef_public_key_pem = self._get_public_keys().get('symmetric')
        public_key = serialization.load_pem_public_key(ksef_public_key_pem.encode('utf-8'))
        key_padding = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        encrypted_symmetric_key = public_key.encrypt(raw_symmetric_key, key_padding)
        return {
            'raw_symmetric_key': self.b64(raw_symmetric_key),
            'encrypted_symmetric_key': self.b64(encrypted_symmetric_key),
            'raw_iv': self.b64(raw_iv),
        }

    def download_batch_status(self, name):
        response = self._make_request('GET', f'{self.api_url}/invoices/exports/{name}')
        json_response = response.json()
        _logger.debug("KSeF batch %s status response:\n%s", name, self.pretty_json(json_response))

        return {
            'name': name,
            'content': json_response,
            'part_ids': [
                Command.create({
                    'batch_name': name,
                    'part_number': part['ordinalNumber'],
                    'download_url': part['url'],
                    'download_method': (part['method'] or '').upper(),
                })
                for part in json_response.get('package', {}).get('parts', [])
            ],
        }

    def download_batch_request(self, date_from, date_to, encryption_data, subject_type=ROLES['buyer']):
        response = self._make_request(
            'POST',
            f'{self.api_url}/invoices/exports',
            json={
                'encryption': {
                    'encryptedSymmetricKey': encryption_data['encrypted_symmetric_key'],
                    'initializationVector': encryption_data['raw_iv'],
                },
                'filters': {
                    'dateRange': {
                        'dateType': 'Invoicing',
                        'from': date_from.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                        'to': date_to.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    },
                    'subjectType': subject_type,
                },
            },
        )
        return response.json()
