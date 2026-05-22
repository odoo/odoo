# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

from .baiwang_client import BaiwangClient

_logger = logging.getLogger(__name__)


class L10nCnEdiDocument(models.Model):
    _name = 'l10n_cn_edi.document'
    _description = 'Baiwang EDI Document (Red Form Tracking)'
    _order = 'create_date desc'

    move_id = fields.Many2one('account.move', string="Credit Note", required=True, ondelete='cascade')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('red_form_pending', 'Pending Confirmation'),
        ('red_form_confirmed', 'Confirmed'),
        ('failed', 'Failed/Rejected'),
    ], default='draft')

    baiwang_uuid = fields.Char(string="Red Form UUID", copy=False)
    baiwang_red_form_number = fields.Char(string="Red Form Number", copy=False)
    baiwang_confirm_state = fields.Char(string="Confirm State Code", copy=False)
    baiwang_red_invoice_no = fields.Char(string="Red Invoice Number", copy=False)
    error_message = fields.Text(string="Error Details")

    @api.model
    def _cron_check_red_form_status(self):
        """
        Scheduled action to poll Baiwang for the status of pending Red Forms.
        Called by ir.cron every hour.
        """
        pending_docs = self.search([
            ('state', '=', 'red_form_pending'),
            ('baiwang_uuid', '!=', False),
        ])

        if not pending_docs:
            return

        _logger.info("Baiwang EDI: Polling %d pending red forms...", len(pending_docs))

        # Group by company to reuse client connections
        docs_by_company = {}
        for doc in pending_docs:
            company = doc.move_id.company_id
            docs_by_company.setdefault(company, self.env['l10n_cn_edi.document'])
            docs_by_company[company] |= doc

        for company, docs in docs_by_company.items():
            try:
                client = BaiwangClient(company)
            except Exception as e:
                _logger.error("Baiwang EDI: Failed to init client for company %s: %s", company.name, e)
                continue

            for doc in docs:
                try:
                    result = client.query_red_form_detail(doc.baiwang_uuid)

                    if result.get('success'):
                        resp_list = result.get('response', [])
                        if resp_list:
                            resp_data = resp_list[0]
                            confirm_state = resp_data.get('confirmState')
                            doc.baiwang_confirm_state = confirm_state

                            if confirm_state in ('01', '04'):
                                # Confirmed (01=auto-approved, 04=both parties confirmed)
                                doc.write({
                                    'state': 'red_form_confirmed',
                                    'baiwang_red_form_number': resp_data.get('redConfirmNo', doc.baiwang_red_form_number),
                                    'baiwang_red_invoice_no': resp_data.get('redInvoiceNo', ''),
                                })
                                doc.move_id.l10n_cn_baiwang_state = 'issued'
                                doc.move_id.message_post(body=self.env._(
                                    "Red Form confirmed! No: %(no)s. Red Invoice: %(inv)s",
                                    no=resp_data.get('redConfirmNo', ''),
                                    inv=resp_data.get('redInvoiceNo', 'pending'),
                                ))

                            elif confirm_state in ('02', '03'):
                                # Still pending (02=waiting buyer, 03=waiting seller)
                                pass

                            elif confirm_state in ('05', '06', '07', '08', '09', '10'):
                                # Rejected/cancelled/expired
                                doc.write({
                                    'state': 'failed',
                                    'error_message': self.env._("Red Form rejected/cancelled. State code: %s", confirm_state),
                                })
                                doc.move_id.l10n_cn_baiwang_state = 'failed'
                                doc.move_id.message_post(body=self.env._(
                                    "Red Form rejected/cancelled. State code: %(state)s",
                                    state=confirm_state,
                                ))
                    else:
                        error_msg = result.get('errorResponse', {}).get('message', 'Unknown Error')
                        _logger.warning("Baiwang EDI: Query failed for UUID %s: %s", doc.baiwang_uuid, error_msg)

                except Exception as e:
                    _logger.error("Baiwang EDI: Error polling UUID %s: %s", doc.baiwang_uuid, e)

        if not self.env.context.get('test_enable'):
            self.env.cr.commit()
