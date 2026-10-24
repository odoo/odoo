import logging
import tempfile
import zipfile

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidKey, InvalidSignature, UnsupportedAlgorithm

from odoo import api, fields, models, modules
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service

_logger = logging.getLogger(__name__)


CHUNK_SIZE = 64 * 1024
HTTP_METHODS = [(method, method) for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')]


class BatchDownloadPart(models.Model):
    _name = 'l10n_pl_edi_batch.part'
    _inherits = {'ir.attachment': 'attachment_id'}
    _description = 'KSeF Batch download part'

    _order = 'batch_name, part_number'

    company_id = fields.Many2one(related='batch_id.company_id')
    batch_name = fields.Char("KSeF batch name", related='batch_id.name')
    part_name = fields.Char(compute="_compute_part_name")
    part_number = fields.Integer("KSeF part ordinal number", readonly=True, required=True)

    download_method = fields.Selection(selection=HTTP_METHODS, readonly=True, required=True)
    download_url = fields.Char(readonly=True, required=True)

    batch_id = fields.Many2one(comodel_name='l10n_pl_edi_batch.download', readonly=True, required=True)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', string="Related attachment", required=True, ondelete='cascade')

    def unlink(self):
        attachments = self.attachment_id
        return super().unlink() and attachments.unlink()

    @api.depends('download_url')
    def _compute_part_name(self):
        for record in self:
            record.part_name = Service._url_to_name(record.download_url)

    def _decrypt_stream(self, response_stream):
        self.ensure_one()
        key, iv = Service.u64(self.batch_id.raw_symmetric_key), Service.u64(self.batch_id.raw_iv)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        for chunk in (chk for chk in response_stream.iter_content(chunk_size=CHUNK_SIZE) if chk):
            decrypted_chunk = decryptor.update(chunk)
            yield unpadder.update(decrypted_chunk)
        yield unpadder.update(decryptor.finalize()) + unpadder.finalize()

    def download(self, commit=True):
        for record in self:
            with tempfile.NamedTemporaryFile(mode='w+b') as tmpf:
                try:
                    response = requests.request(record.download_method, record.download_url, stream=True)
                    response.raise_for_status()
                    for decrypted_chunk in record._decrypt_stream(response):
                        tmpf.write(decrypted_chunk)
                except (
                    requests.RequestException, ValueError, TypeError,
                    InvalidKey, InvalidSignature, UnsupportedAlgorithm,
                ) as e:
                    _logger.warning("Couldn't download KSeF batch %s: %s", record.part_name, e)
                    continue
                tmpf.flush()
                tmpf.seek(0)
                content = tmpf.read()
            record.attachment_id = self.env['ir.attachment'].sudo().create({
                'name': record.part_name,
                'description': record.batch_name,
                'type': 'binary',
                'mimetype': 'application/zip',
                'company_id': record.batch_id.company_id.id,
                'res_model': record._name,
                'res_id': record.id,
                'res_field': 'attachment_id',
                'raw': content,
            }).with_env(record.env)
            _logger.info("KSeF Batch part %s downloaded succesfully", record.part_name)
            if commit and not modules.module.current_test:
                self.env.cr.commit()

    def unzip(self, commit=True):
        if not self:
            raise ValueError("No part was selected for unzip")
        batches = self.mapped("batch_id")
        company = self[0].company_id
        attachments = self.env['ir.attachment']
        sorted_parts = self.sorted(key=lambda a: a.name).filtered(lambda a: a.file_size > 0)
        with tempfile.TemporaryFile(mode='w+b') as temp_zip_stream:
            for part in sorted_parts:
                temp_zip_stream.write(part.raw)
            temp_zip_stream.seek(0)
            existing_names = batches.attachment_ids.mapped("name")
            with zipfile.ZipFile(temp_zip_stream, 'r') as zf:
                zipped_names = [
                    name
                    for name in zf.namelist()
                    if '.json' not in name
                    and name not in existing_names
                ]
                for xml_name in zipped_names:
                    with zf.open(xml_name) as xml_file:
                        content = xml_file.read()
                        attachment = self.env['ir.attachment'].sudo().create({
                            'name': xml_name,
                            'mimetype': 'application/xml',
                            'company_id': company.id,
                            'res_model': 'l10n_pl_edi_batch.download',
                            'res_id': batches.id,
                            'raw': content,
                        }).with_env(self.env)
                        attachments |= attachment
                        if commit and not modules.module.current_test:
                            self.env.cr.commit()
        batches.attachment_ids |= attachments
        return batches.attachment_ids
