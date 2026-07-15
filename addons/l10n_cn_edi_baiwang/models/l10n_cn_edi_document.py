# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient

_logger = logging.getLogger(__name__)


class L10nCnEdiDocument(models.Model):
    _name = 'l10n_cn_edi.document'
    _description = 'Baiwang EDI Document (Red Form Tracking)'
    _order = 'id desc'

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
    baiwang_red_form_amount_total = fields.Float(string="Credit Price", copy=False)
    baiwang_red_form_amount_tax = fields.Float(string="Credit Tax", copy=False)
    error_message = fields.Text(string="Error Details")

    @api.model
    def _cron_check_red_form_status(self):
        """
        Scheduled action to poll Baiwang for the status of pending Red Forms.
        Called by ir.cron every hour.
        """
        # ponytail: check for inbound red forms first so early returns don't skip it
        self._pull_inbound_red_forms()

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
            client = BaiwangClient(company)

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
                                red_inv_no = resp_data.get('redInvoiceNo', '')
                                raw_date = resp_data.get('redInvoiceDate', '')

                                doc.write({
                                    'state': 'red_form_confirmed',
                                    'baiwang_red_form_number': resp_data.get('redConfirmNo', doc.baiwang_red_form_number),
                                    'baiwang_red_invoice_no': red_inv_no,
                                })

                                # ponytail: guard against overwriting the Blue Invoice's fapiao number
                                if doc.move_id.move_type == 'out_refund':
                                    vals = {'l10n_cn_baiwang_state': 'issued'}
                                    if red_inv_no:
                                        vals['l10n_cn_baiwang_invoice_no'] = red_inv_no

                                    if raw_date and len(raw_date) >= 14:
                                        vals['l10n_cn_baiwang_invoice_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]} {raw_date[8:10]}:{raw_date[10:12]}:{raw_date[12:14]}"
                                    else:
                                        vals['l10n_cn_baiwang_invoice_date'] = fields.Datetime.now()

                                    doc.move_id.write(vals)
                                    doc.move_id.activity_schedule(
                                        'mail.mail_activity_data_todo',
                                        summary=self.env._("Red Form has been approved and Red Fapiao has been issued, Please confirm Credit Note in Odoo accordingly"),
                                        user_id=doc.move_id.create_uid.id,
                                    )
                                else:
                                    doc.move_id.activity_schedule(
                                        'mail.mail_activity_data_todo',
                                        summary=self.env._("Inbound Red Form %s approved and issued. Please ensure a matching Credit Note is posted.", doc.baiwang_red_form_number),
                                        user_id=doc.move_id.create_uid.id,
                                    )

                            elif confirm_state in ('02', '03'):
                                # Still pending
                                pass

                            elif confirm_state in ('05', '06', '07', '08', '09', '10'):
                                doc.write({
                                    'state': 'failed',
                                    'error_message': self.env._("Red Form rejected/cancelled. State code: %s", confirm_state),
                                })
                                # ponytail: only fail the move if it's the refund
                                if doc.move_id.move_type == 'out_refund':
                                    doc.move_id.l10n_cn_baiwang_state = 'failed'
                                doc.move_id.message_post(body=self.env._(
                                    "Red Form rejected/cancelled. State code: %(state)s",
                                    state=confirm_state,
                                ))
                    else:
                        error_msg = result.get('errorResponse', {}).get('message', 'Unknown Error')
                        _logger.warning("Baiwang EDI: Query failed for UUID %s: %s", doc.baiwang_uuid, error_msg)

                except UserError as e:
                    _logger.error("Baiwang EDI: Error polling UUID %s: %s", doc.baiwang_uuid, e)

    @api.model
    def _pull_inbound_red_forms(self):
        """Poll Baiwang for inbound red forms awaiting our approval (Buyer role)."""
        companies = self.env['res.company'].search([('l10n_cn_baiwang_subscription_status', '=', 'authorized')])
        for company in companies:
            client = BaiwangClient(company)
            try:
                # buySelSelector: 1=Buyer role, confirmState: 02=Waiting Buyer Approval
                res = client.query_red_form_list({
                    'buySelSelector': '1',
                    'confirmState': '02',
                    'entryIdentity': '02',
                    'buyerTaxNo': company.vat,
                    'sellerTaxNo': '',
                })
                form_list = res.get('response', [])
                if not isinstance(form_list, list):
                    continue

                for form in form_list:
                    uuid = form.get('redConfirmUuid')
                    amt_total = float(form.get('invoiceTotalPrice', 0.0))
                    amt_tax = float(form.get('invoiceTotalTax', 0.0))
                    if not uuid or self.search_count([('baiwang_uuid', '=', uuid)]):
                        continue

                    # Match against Vendor Bills where we are the buyer
                    blue_move = self.env['account.move'].search([
                        ('l10n_cn_baiwang_invoice_no', '=', form.get('originalInvoiceNo')),
                        ('company_id', '=', company.id),
                        ('move_type', '=', 'in_invoice'),
                    ], limit=1)

                    if not blue_move:
                        continue

                    self.create({
                        'move_id': blue_move.id,
                        'state': 'red_form_pending',
                        'baiwang_uuid': uuid,
                        'baiwang_red_form_number': form.get('redConfirmNo'),
                        'baiwang_confirm_state': '02',
                        'baiwang_red_form_amount_total': float(form.get('invoiceTotalPrice', 0.0)),
                        'baiwang_red_form_amount_tax': float(form.get('invoiceTotalTax', 0.0)),
                    })

                    blue_move.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=self.env._(
                            "Inbound Red Form %(number)s requires approval (Price: %(price)s, Tax: %(tax)s)",
                            number=form.get('redConfirmNo'), price=amt_total, tax=amt_tax,
                        ),
                        user_id=blue_move.create_uid.id,
                    )
            except Exception as e:
                _logger.error("Baiwang EDI: Error pulling inbound red forms for company %s: %s", company.name, e)
