import json
import logging
import tempfile
import zipfile

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import models, modules
from odoo.osv import expression
from odoo.addons.l10n_pl_edi.models.account_move import KSEF_LOG_HEADER
from odoo.addons.l10n_pl_edi.tools import u64

_logger = logging.getLogger(__name__)

CRON_NAME = 'l10n_pl_edi.cron_l10n_pl_edi_download_batches'
CHUNK_SIZE = 64 * 1024


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_pl_edi_get_parts(self, extra_domain=None):
        parts = self.search([
            *expression.OR([[('name', 'ilike', '%.zip.aes')], [('name', 'ilike', '%.zip')]]),
            ('type', '=', 'binary'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self.env.ref(CRON_NAME).id),
            *(extra_domain or []),
        ], order="create_date desc")
        return parts.grouped('description')

    def _l10n_pl_edi_create_batch(self, batch_number, payload):
        if isinstance(payload, dict):
            payload = json.dumps(payload, indent=4).encode()
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

    def _l10n_pl_edi_download_parts(self, batch_data, commit=True):
        self.ensure_one()
        batch_number = batch_data['number']
        existing_parts = self._l10n_pl_edi_get_parts(extra_domain=[('description', '=', batch_number)])
        new_parts = Attachment = self.env['ir.attachment']
        for part_name, part_data in [
            (name, batch_data['parts'][name])
            for name in batch_data['parts']
            if name not in existing_parts.get(batch_number, Attachment).mapped("name")
        ]:
            response = requests.request(part_data['method'], part_data['url'], stream=True)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(mode='w+b') as tmpf:
                number, filename = batch_data['number'], part_name.replace('.aes', '')
                for decrypted_chunk in self._l10n_pl_edi_decrypt_stream(response, batch_data['encryption_data']):
                    tmpf.write(decrypted_chunk)
                tmpf.flush()
                tmpf.seek(0)
                _logger.info("%s Finished downloading part %s", KSEF_LOG_HEADER, part_name)
                new_parts |= self.create({
                    **self._l10n_pl_edi_attachment_vals(),
                    'company_id': batch_data['company_id'],
                    'name': filename,
                    'description': number,
                    'raw': tmpf.read(),
                })
                _logger.info("%s Attachment %s created", KSEF_LOG_HEADER, filename)
            if commit and not modules.module.current_test:
                self.env.cr.commit()

        return new_parts

    def _l10n_pl_edi_attachment_vals(self):
        return {
            'type': 'binary',
            'mimetype': 'application/zip',
            'res_model': 'ir.cron',
            'res_id': self.env.ref(CRON_NAME).id,
        }

    def _l10n_pl_edi_decrypt_stream(self, response_stream, encryption_data):
        raw_key = u64(encryption_data['raw_symmetric_key'])
        raw_iv = u64(encryption_data['raw_iv'])
        cipher = Cipher(algorithms.AES(raw_key), modes.CBC(raw_iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        for chunk in (chk for chk in response_stream.iter_content(chunk_size=CHUNK_SIZE) if chk):
            decrypted_chunk = decryptor.update(chunk)
            yield unpadder.update(decrypted_chunk)
        yield unpadder.update(decryptor.finalize()) + unpadder.finalize()

    def _l10n_pl_edi_decompress(self):
        company = self[0].company_id
        attachments_data = []
        sorted_parts = self.sorted(key=lambda a: a.name)
        with tempfile.TemporaryFile(mode='w+b') as temp_zip_stream:
            for part in sorted_parts:
                temp_zip_stream.write(part.raw)
            temp_zip_stream.seek(0)
            with zipfile.ZipFile(temp_zip_stream, 'r') as zf:
                for xml_name in zf.namelist():
                    with zf.open(xml_name) as xml_file:
                        attachments_data.append({
                            'mimetype': 'application/xml',
                            'name': xml_name,
                            'company_id': company.id,
                            'raw': xml_file.read(),
                        })
        sorted_parts.unlink()
        return self.create(attachments_data)
