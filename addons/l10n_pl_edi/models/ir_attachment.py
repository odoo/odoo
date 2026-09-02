import json
import logging
import shutil
from pathlib import Path

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import models
from odoo.osv import expression
from odoo.addons.l10n_pl_edi.tools import u64

_logger = logging.getLogger(__name__)

CRON_NAME = 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills'
BUFFER_SIZE = 65536


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_pl_edi_create_batch(self, batch_number, payload):
        if isinstance(payload, str):
            payload = payload.encode()
        return self.create({
            'name': f'ksef_batch_{batch_number}.json',
            'type': 'binary',
            'mimetype': 'application/json',
            'res_model': 'ir.cron',
            'res_id': self.env.ref(CRON_NAME).id,
            'raw': payload or b'',
        })

    def _l10n_pl_edi_get_batches(self):
        return self.search([
            ('name', 'ilike', 'ksef_batch_%.json'),
            ('type', '=', 'binary'),
            ('mimetype', '=', 'application/json'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self.env.ref(CRON_NAME).id),
        ], order="create_date desc")

    def merge(self, dest_name, res_model=False, res_id=False, delete=False):
        """ Merge current attachments into a new one """
        if not self:
            raise ValueError("You cannot merge no attachments")
        dest = self.create({'name': dest_name, 'type': 'binary', 'raw': b'', 'res_model': res_model, 'res_id': res_id})
        dest_path = Path(dest._full_path(dest.store_fname))

        with dest_path.open('wb') as f_out:
            for att in self:
                with Path(att._full_path(att.store_fname)).open('rb') as f_in:
                    shutil.copyfileobj(f_in, f_out, length=BUFFER_SIZE)

        dest.file_size = dest_path.stat().st_size
        if delete:
            self.unlink()
        return dest

    def _l10n_pl_edi_download_parts(self):
        self.ensure_one()
        batch_data = json.loads(self.raw.decode())
        encryption_data = batch_data['encryption_data']
        cipher = Cipher(
            algorithms.AES(u64(encryption_data['raw_symmetric_key'])),
            modes.CBC(u64(encryption_data['raw_iv'])),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()

        create_data = []
        for part_name, part_data in batch_data['parts'].items():
            requests_method, url = {'GET': requests.get, 'POST': requests.post}[part_data['method']], part_data['url']
            try:
                response = requests_method(url, timeout=30)
                response.raise_for_status()
                encrypted_data = response.content
            except Exception:
                _logger.exception()
                return False

            decrypted_bytes = decryptor.update(encrypted_data) + decryptor.finalize()
            decrypted_bytes = unpadder.update(decrypted_bytes) + unpadder.finalize()
            create_data.append({
                'name': part_data['name'].replace('.aes', ''),
                'type': 'binary',
                'mimetype': 'application/zip',
                'description': batch_data['number'],
                'res_model': 'ir.cron',
                'res_id': self.env.ref(CRON_NAME).id,
                'raw': decrypted_bytes,
            })
        existing_parts = self._l10n_pl_edi_get_parts()
        new_parts = self.sudo().create([x for x in create_data if x['name'] not in existing_parts.mapped("name")])
        for part in new_parts:
            _logger.info("Created part %s/%s", part.description, part.name)
        return new_parts.with_env(self.env)

    def _l10n_pl_edi_get_parts(self, extra_domain=None):
        return self.sudo().search([
            *expression.OR([[('name', 'ilike', '%.zip.aes')], [('name', 'ilike', '%.zip')]]),
            ('type', '=', 'binary'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self.env.ref(CRON_NAME).id),
            *(extra_domain or []),
        ], order="create_date desc").with_env(self.env)
