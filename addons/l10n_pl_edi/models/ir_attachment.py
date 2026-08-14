import logging

from odoo import models


_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _l10n_pl_edi_get_batches(self, batch_number="[0-9a-zA-Z]+"):
        return self.search([
            ('name', 'ilike', f'ksef_batch_{batch_number}.json'),
            ('type', '=', 'binary'),
            ('mimetype', '=', 'application/json'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self._l10n_pl_edi_get_cron().id),
        ], order="create_date desc")

    def _l10n_pl_edi_set_batch(self, batch_number, payload):
        if batch := self._l10n_pl_edi_get_batches(batch_number):
            batch.raw = payload.encode() if payload else b''
            return batch

        return self.create({
            'name': f'ksef_batch_{batch_number}.json',
            'type': 'binary',
            'mimetype': 'application/json',
            'res_model': 'ir.cron',
            'res_id': self._l10n_pl_edi_get_cron().id,
        })

    def _l10n_pl_edi_get_cron(self):
        return self.env.ref('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

    def _l10n_pl_edi_get_parts(self, company, extra_domain=None):
        return self.search([
            ('name', 'ilike', '%.zip.aes'),
            ('type', '=', 'binary'),
            ('res_model', '=', 'ir.cron'),
            ('res_id', '=', self._l10n_pl_edi_get_cron().id),
            *(extra_domain or []),
        ], order="create_date desc")

    def _l10n_pl_edi_set_part(self, company, number, name, method, url):
        return self.create({
            'name': name,
            'description': f"{method.upper()} {url}",
            'type': 'binary',
            'res_model': 'ir.cron',
            'res_id': self._l10n_pl_edi_get_cron().id,
        })
