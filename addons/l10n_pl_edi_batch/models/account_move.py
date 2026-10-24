import json
import logging
import time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, modules

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi_batch.tools import KsefApiServiceBatch as Service

KSEF_WINDOW = 30
KSEF_FIRST_DAY = fields.Date.from_string('2026-01-31')
KSEF_LOG_HEADER = "KSeF download:"

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_pl_edi_trigger(self, cron_ref, seconds=5):
        retry_at = fields.Datetime.now() + relativedelta(seconds=seconds)
        _logger.info("%s Retriggering (%s)...", KSEF_LOG_HEADER, retry_at)
        self.env.ref(cron_ref)._trigger(at=retry_at)

    @api.model
    def _cron_l10n_pl_edi_download_bills(self):
        return
        today = fields.Date.today()
        try:
            for company in self.env['res.company'].search([('l10n_pl_edi_access_token', '!=', False)]):
                if self._l10n_pl_edi_request_bills(company, today, today + relativedelta(days=1)):
                    self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_download_batches')
        except KSeFRateLimitError as e:
            self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills', e.retry_after)

    @api.model
    def _cron_l10n_pl_edi_ksef_download_historic_bills(self):
        return
        Attachment = self.env['ir.attachment']
        today, now = fields.Date.today(), fields.Datetime.now()
        batch_data = {batch: json.loads(batch.raw) for batch in Attachment._l10n_pl_edi_get_batches()}

        # Clear expired batches
        if expired_batches := Attachment.union(*[
            batch for batch, batch_values in batch_data.items()
            if fields.Datetime.from_string(batch_values.get('date_expiry')) < now
        ]):
            expired_batches.unlink()

        # Query for historic invoices per company
        try:  # ruff: ignore [too-many-statements-in-try-clause]
            for company in self.env['res.company'].search([('l10n_pl_edi_access_token', '!=', False)]):
                param_name = f'l10n_pl_edi.last_historic_date_{company.id}'
                date_to = fields.Date.from_string(self.env['ir.config_parameter'].get_param(param_name, fields.Date.to_string(today)))
                if date_to and date_to > KSEF_FIRST_DAY:
                    date_from = max(KSEF_FIRST_DAY, date_to + relativedelta(days=-KSEF_WINDOW))
                    if self._l10n_pl_edi_request_bills(company, date_from, date_to):
                        self.env['ir.config_parameter'].set_param(param_name, fields.Date.to_string(date_from))
                        self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_download_batches')
        except KSeFRateLimitError as e:
            self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_historic_bills', e.retry_after)

    def _l10n_pl_edi_request_bills(self, company, date_from, date_to):
        service = Service(company)
        encryption_data = service._create_encryption_data()
        if batch_ticket := service.download_batch_request(date_from, date_to, encryption_data):
            for delay in (5, 7, 18, 30, None):
                batch_number = batch_ticket['number']
                status_data = service.download_batch_status(company, batch_number, date_from, date_to, encryption_data)
                status = int(status_data['status'] or '')
                if status == 100:
                    if not delay:
                        break
                    time.sleep(delay)
                    continue
                if status == 200:
                    self.env['ir.attachment']._l10n_pl_edi_create_batch(status_data['number'], status_data)
                    return True
                _logger.warning('%s Batch %s couldn\'t be downloaded (%s): %s', KSEF_LOG_HEADER, batch_number, status, status_data['error'])
                break
        return False

    def _cron_l10n_pl_edi_download_batches(self):
        Attachment = self.env['ir.attachment']
        # Always download latest batches first
        if batches := Attachment._l10n_pl_edi_get_batches():
            # We cannot use SQL or the ORM to read inside the JSON content
            (batch, batch_data) = max(
                ((batch, json.loads(batch.raw)) for batch in batches),
                key=lambda x: fields.Date.from_string(x[1]['date_to']),
            )
            if batch and batch_data:
                batch_name = batch.name
                _logger.info("%s Downloading batch: %s ...", KSEF_LOG_HEADER, batch.name)
                Attachment._l10n_pl_edi_download_parts(batch_data)
                batch.unlink()
                _logger.info("%s Deleted batch: %s", KSEF_LOG_HEADER, batch_name)
                # Retrigger to download the next batch
                self._l10n_pl_edi_trigger('l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')
                return

        for company in self.env['res.company'].search([('l10n_pl_edi_access_token', '!=', False)]):
            # Only decompress sets of parts that have no batch file pending
            batches = Attachment._l10n_pl_edi_get_batches()
            batches_numbers = batches.mapped('description') if batches else []
            part_groups = {
                number: parts
                for number, parts in Attachment._l10n_pl_edi_get_parts().items()
                if number not in batches_numbers
            }
            for number, parts in part_groups.items():
                attachments = parts._l10n_pl_edi_decompress()
                for attachment in attachments:
                    move = self.create([{
                        'company_id': company.id,
                        'move_type': 'in_invoice',
                    }])
                    move.message_post(body=self.env._("KSeF bill %s has been attached", attachment.name), attachment_ids=attachment.ids)
                    attachment.write({
                        'company_id': company.id,
                        'description': self.env._('KSeF Received Bill XML'),
                        'res_id': move.id,
                        'res_model': move._name,
                        'res_field': 'l10n_pl_edi_attachment_file',
                    })
                    move.write({
                        'l10n_pl_edi_attachment_id': attachment.id,
                        'l10n_pl_edi_status': 'fetched',
                        'l10n_pl_edi_header': 'Fetched From KSeF',
                    })
                    move.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
                if not modules.module.current_test:
                    self.env.cr.commit()
