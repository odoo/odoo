import tempfile

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from odoo import api, fields, models, modules
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import url_to_name, u64


CHUNK_SIZE = 64 * 1024
HTTP_METHODS = [(method, method) for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')]
CRON_NAME = 'l10n_pl_edi.cron_l10n_pl_edi_download_batches'


class BatchDownloadPart(models.Model):
    _name = 'l10n_pl_edi_batch.part'
    _inherits = {'ir.attachment': 'attachment_id'}
    _description = 'KSeF Batch download part'

    _order = 'batch_name, part_number'

    batch_id = fields.Many2one(comodel_name='l10n_pl_edi_batch.download', readonly=True, required=True)
    company_id = fields.Many2one(related='batch_id.company_id')
    batch_name = fields.Char("KSeF batch name", related='batch_id.name')
    part_name = fields.Char(compute="_compute_part_name")
    part_number = fields.Integer("KSeF part ordinal number", readonly=True, required=True)
    download_method = fields.Selection(selection=HTTP_METHODS, readonly=True, required=True)
    download_url = fields.Char(readonly=True, required=True)
    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Related attachment",
        required=True,
        ondelete='cascade',
    )

    def unlink(self):
        attachments = self.attachment_id
        return super().unlink() and attachments.unlink()

    @api.depends('download_url')
    def _compute_part_name(self):
        for record in self:
            record.part_name = url_to_name(record.download_url)

    def _decrypt_stream(self, response_stream):
        self.ensure_one()
        key, iv = u64(self.batch_id.raw_symmetric_key), u64(self.batch_id.raw_iv)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        for chunk in (chk for chk in response_stream.iter_content(chunk_size=CHUNK_SIZE) if chk):
            decrypted_chunk = decryptor.update(chunk)
            yield unpadder.update(decrypted_chunk)
        yield unpadder.update(decryptor.finalize()) + unpadder.finalize()

    def download(self, commit=True):
        for record in self:
            response = requests.request(record.download_method, record.download_url, stream=True)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(mode='w+b') as tmpf:
                for decrypted_chunk in record._decrypt_stream(response):
                    tmpf.write(decrypted_chunk)
                tmpf.flush()
                tmpf.seek(0)
                record.attachment_id = self.env['ir.attachment'].sudo().create({
                    'company_id': record.batch_id.company_id.id,
                    'name': record.part_name,
                    'description': record.batch_name,
                    'raw': tmpf.read(),
                    'type': 'binary',
                    'mimetype': 'application/zip',
                    'res_model': 'ir.cron',
                    'res_id': self.env.ref(CRON_NAME).id,
                }).with_env(record.env)
            if commit and not modules.module.current_test:
                self.env.cr.commit()
