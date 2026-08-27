# import json
import logging
import shutil
# from base64 import b64decode
from pathlib import Path

# import requests
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import padding
# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import models
# from odoo.osv import expression

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

    def _l10n_pl_edi_get_batches(self, batch_number="%"):
        return self.search([
            ('name', 'ilike', f'ksef_batch_{batch_number}.json'),
            ('type', '=', 'binary'),
            ('mimetype', '=', 'application/json'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self.env.ref(CRON_NAME).id),
        ], order="create_date desc")

    def merge(self, dest_name, res_model=False, res_id=False):
        if not self:
            raise ValueError("You cannot merge no attachments")
        dest = self.create({'name': dest_name, 'type': 'binary', 'raw': b'', 'res_model': res_model, 'res_id': res_id})
        dest_path = Path(dest._full_path(dest.store_fname))

        with dest_path.open('wb') as f_out:
            for att in self:
                with Path(att._full_path(att.store_fname)).open('rb') as f_in:
                    shutil.copyfileobj(f_in, f_out, length=BUFFER_SIZE)

        dest.file_size = dest_path.stat().st_size
        self.unlink()
        return dest

    # def _l10n_pl_edi_download_parts(self, batch_data):
    #     symmetric_key = b64decode(batch_data['encryption']['symmetric_key'])
    #     iv = b64decode(batch_data['encryption']['iv'])
    #     cipher = Cipher(algorithms.AES(symmetric_key), modes.CBC(iv), backend=default_backend())
    #     decryptor = cipher.decryptor()
    #     unpadder = padding.PKCS7(128).unpadder()

    #     for part in self:
    #         part_data = batch_data['parts'][part.name]
    #         requests_method, url = {'GET': requests.get, 'POST': requests.post}[part_data['method']], part_data['url']
    #         try:
    #             response = requests_method(url, timeout=30)
    #             response.raise_for_status()
    #             encrypted_data = response.content
    #         except Exception:
    #             _logger.exception()
    #             return False

    #         decrypted_bytes = decryptor.update(encrypted_data) + decryptor.finalize()
    #         decrypted_bytes = unpadder.update(decrypted_bytes) + unpadder.finalize()
    #         part.raw = decrypted_bytes

    # def _l10n_pl_edi_get_batch_info(self):
    #     batch_fullpath = self._full_path(self.store_fname)
    #     return json.load(batch_fullpath)

    # def _l10n_pl_edi_get_cron(self):
    #     return self.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

    # def _l10n_pl_edi_get_parts(self, company, extra_domain=None):
    #     return self.search([
    #         *expression.OR([[('name', 'ilike', '%.zip.aes')], [('name', 'ilike', '%.zip')]]),
    #         ('type', '=', 'binary'),
    #         ('res_model', '=', 'ir.cron'),
    #         ('res_id', '=', self._l10n_pl_edi_get_cron().id),
    #         *(extra_domain or []),
    #     ], order="create_date desc")

    # def _l10n_pl_edi_set_parts(self, company, parts):
    #     if not parts:
    #         return self.env['ir.attachment']
    #     names = set(parts.mapped('name'))
    #     old = self._l10n_pl_edi_get_parts(company, [('name', 'in', names)])
    #     return old + self.create([
    #         {
    #             'name': part['name'],
    #             'description': part['batch_number'],
    #             'type': 'binary',
    #             'res_model': 'ir.cron',
    #             'res_id': self._l10n_pl_edi_get_cron().id,
    #         }
    #         for part in parts
    #         if part['name'] not in old.mapped('name')
    #     ])
