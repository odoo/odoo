import logging
import tempfile

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidKey, InvalidSignature, UnsupportedAlgorithm

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service

_logger = logging.getLogger(__name__)


CHUNK_SIZE = 64 * 1024
HTTP_METHODS = [(method, method) for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')]


class BatchDownloadPart(models.Model):
    _name = 'l10n_pl_edi_batch.part'
    _description = 'KSeF Batch download part'

    _order = 'batch_id, part_number'

    company_id = fields.Many2one(related='batch_id.company_id')
    batch_name = fields.Char("KSeF batch name", related='batch_id.name')
    part_name = fields.Char(compute="_compute_part_name")
    part_number = fields.Integer("KSeF part ordinal number", readonly=True, required=True)

    download_method = fields.Selection(selection=HTTP_METHODS, readonly=True, required=True)
    download_url = fields.Char(readonly=True, required=True)

    batch_id = fields.Many2one(comodel_name='l10n_pl_edi_batch.download', readonly=True, required=True)
    decrypted_file = fields.Binary("Decrypted part", attachment=True, readonly=True, copy=False)

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

    def _store_decrypted_file(self, content):
        """ Store the decrypted slice of the ZIP as the attachment of `decrypted_file`, named after the part
            without its .aes: with a .zip name, Odoo doesn't guess its mimetype from the first bytes, which fails
            on a slice that isn't a whole ZIP and logs a warning. """
        self.ensure_one()
        self.env['ir.attachment'].create({
            'name': self.part_name.removesuffix('.aes'),
            'res_model': self._name,
            'res_field': 'decrypted_file',
            'res_id': self.id,
            'raw': content,
        })
        # Not written through the field: drop its cached values (bin_size reads included), and have the
        # fields that depend on it, like the batch's state, recomputed
        self.invalidate_recordset(['decrypted_file'])
        self.modified(['decrypted_file'])

    def download(self):
        """ Download and decrypt the parts. A failure raises a UserError with the reason. """
        for record in self:
            with tempfile.NamedTemporaryFile(mode='w+b') as tmpf:
                try:
                    response = requests.request(record.download_method, record.download_url, stream=True)
                    _logger.debug("KSeF part download %s %s %s", record.download_method, record.download_url, response.status_code)
                    response.raise_for_status()
                    for decrypted_chunk in record._decrypt_stream(response):
                        tmpf.write(decrypted_chunk)
                except (
                    requests.RequestException, ValueError, TypeError,
                    InvalidKey, InvalidSignature, UnsupportedAlgorithm,
                ) as e:
                    raise UserError(self.env._("Couldn't download KSeF batch part %(part)s: %(error)s", part=record.part_name, error=e)) from e
                tmpf.flush()
                tmpf.seek(0)
                content = tmpf.read()
            record._store_decrypted_file(content)
            _logger.info("KSeF Batch part %s downloaded succesfully", record.part_name)
