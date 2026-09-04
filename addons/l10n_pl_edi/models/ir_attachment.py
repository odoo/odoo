import json
import logging
import hashlib
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import models
from odoo.osv import expression
from odoo.addons.l10n_pl_edi.tools import u64
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService

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

    def merge(self, dest_name, delete=False, **kwargs):
        if not self:
            raise ValueError("No attachments to merge.")
        if len(self) == 1:
            return self
        dest = self.create({'name': dest_name, 'type': 'binary', 'raw': b' ', **kwargs})
        if self[0].db_datas:
            att_ids = tuple(self.ids)
            # SUBSTRING(... FROM 2) strips the initial 1-byte space allocation
            self.env.cr.execute("""
                UPDATE ir_attachment
                SET db_datas = SUBSTRING((
                    SELECT string_agg(db_datas, ''::bytea)
                    FROM ir_attachment
                    WHERE id IN %s
                    ORDER BY array_position(%s, id)
                ) FROM 2)
                WHERE id = %s
            """, (att_ids, list(self.ids), dest.id))
            self.env.cr.execute("""
                UPDATE ir_attachment
                SET file_size = OCTET_LENGTH(db_datas)
                WHERE id = %s
                RETURNING file_size, encode(SHA1(db_datas), 'hex')
            """, (dest.id,))
            file_size, checksum = self.env.cr.fetchone()
        else:
            sha1 = hashlib.sha1()
            dest_path = Path(dest._full_path(dest.store_fname))
            with dest_path.open('wb') as f_out:
                att_path = [(att, path) for att in self if (path := Path(att._full_path(att.store_fname)))]
                for att, path in att_path:
                    with path.open('rb') as f_in:
                        while chunk := f_in.read(2 ** 20):
                            f_out.write(chunk)
                            sha1.update(chunk)
            file_size, checksum = dest_path.stat().st_size, sha1.hexdigest()
        dest.write({'file_size': file_size, 'checksum': checksum})
        dest.invalidate_recordset(['db_datas'])
        if delete:
            self.unlink()
        return dest

    def _l10n_pl_edi_download_parts(self, company, batch_data, commit=False):
        self.ensure_one()
        service = KsefApiService(company)
        encryption_data = batch_data['encryption_data']
        cipher = Cipher(
            algorithms.AES(u64(encryption_data['raw_symmetric_key'])),
            modes.CBC(u64(encryption_data['raw_iv'])),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        existing_parts_names = self._l10n_pl_edi_get_parts(
            extra_domain=[('description', '=', batch_data['number'])]
        ).mapped("name")
        for existing_part_name in existing_parts_names:
            _logger.info("Existing part : %s", existing_part_name)
        to_download = [
            (name, batch_data['parts'][name])
            for name in batch_data['parts']
            if name not in existing_parts_names
        ]
        new_parts = self.env['ir.attachment']
        for part_name, part_data in to_download:
            response = service._make_request(part_data['method'], part_data['url'], set_auth_header=False)
            encrypted_data = response.content
            decrypted_bytes = decryptor.update(encrypted_data) + decryptor.finalize()
            decrypted_bytes = unpadder.update(decrypted_bytes) + unpadder.finalize()
            filename = part_data['name'].replace('.aes', '')
            new_parts |= self.sudo().create({
                'name': filename,
                'type': 'binary',
                'mimetype': 'application/zip',
                'description': batch_data['number'],
                'res_model': 'ir.cron',
                'res_id': self.env.ref(CRON_NAME).id,
                'raw': decrypted_bytes,
            })
            _logger.info("Downloaded %s (%s)", filename, part_name)
            _logger.info("Created part %s/%s", batch_data['number'], filename)
            if commit:
                self.env.cr.commit()
        return new_parts.with_env(self.env)

    def _l10n_pl_edi_get_parts(self, extra_domain=None):
        return self.sudo().search([
            *expression.OR([[('name', 'ilike', '%.zip.aes')], [('name', 'ilike', '%.zip')]]),
            ('type', '=', 'binary'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self.env.ref(CRON_NAME).id),
            *(extra_domain or []),
        ], order="create_date desc").with_env(self.env)
