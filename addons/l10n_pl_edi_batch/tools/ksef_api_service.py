import json
import os
from datetime import timezone
from dateutil.parser import parse
from pathlib import Path
from urllib.parse import urlparse, unquote

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import fields, Command
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


ROLES = {
    'seller': 'Subject1',
    'buyer': 'Subject2',
    'third_party': 'Subject3',
    'authorized': 'SubjectAuthorized',
}


class KsefApiServiceBatch(KsefApiService):
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
            'raw_symmetric_key': KsefApiService.b64(raw_symmetric_key),
            'encrypted_symmetric_key': KsefApiService.b64(encrypted_symmetric_key),
            'raw_iv': KsefApiService.b64(raw_iv),
        }

    def download_batch_status(self, name):
        response = self._make_request('GET', f'{self.api_url}/invoices/exports/{name}')
        json_response = response.json()

        date_expiry_str = json_response.get('packageExpirationDate') or False
        if date_expiry_str:
            date_expiry_str = fields.Datetime.to_string(
                parse(date_expiry_str).astimezone(timezone.utc).replace(tzinfo=None)
            )

        return {
            'name': name,
            'content': json.dumps(json_response, indent=4),
            'status': f"{json_response['status']['code']}" or False,
            'error': '\n'.join(json_response['status'].get('details', []) or []) or False,
            'date_expiry': date_expiry_str,
            'parts': [
                Command.create({
                    'name': self._url_to_name(part['url']),
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
