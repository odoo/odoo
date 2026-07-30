# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

from .baiwang_client import BaiwangClient
from odoo.addons.l10n_cn_edi_baiwang.models.account_move import RED_FORM_TYPES

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
    baiwang_red_form_type = fields.Selection(selection=RED_FORM_TYPES, string="Red Form Reason", copy=False)
    error_message = fields.Text(string="Error Details")

    @api.model
    def _cron_check_red_form_status(self):
        """
        Scheduled action to poll Baiwang for the status of pending Red Forms.
        Called by ir.cron every hour.
        """
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
                    with self.env.cr.savepoint():
                        # BaiwangClient returns unwrapped response rows; failures raise UserError.
                        resp_list = client.query_red_form_detail(doc.baiwang_uuid)
                        if isinstance(resp_list, list) and resp_list:
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
                                if doc.move_id.move_type == 'out_refund':
                                    vals = {'l10n_cn_baiwang_state': 'issued'}
                                    if red_inv_no:
                                        vals['l10n_cn_baiwang_invoice_no'] = red_inv_no
                                    vals['l10n_cn_baiwang_invoice_date'] = doc.move_id._l10n_cn_baiwang_parse_red_invoice_datetime(raw_date)
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
                                pass
                            elif confirm_state in ('05', '06', '07', '08', '09', '10'):
                                doc.write({
                                    'state': 'failed',
                                    'error_message': self.env._("Red Form rejected/cancelled. State code: %s", confirm_state),
                                })
                                if doc.move_id.move_type == 'out_refund':
                                    doc.move_id.l10n_cn_baiwang_state = 'failed'
                                doc.move_id.message_post(body=self.env._(
                                    "Red Form rejected/cancelled. State code: %(state)s",
                                    state=confirm_state,
                                ))
                except UserError as e:
                    _logger.error("Baiwang EDI: Error polling UUID %s: %s", doc.baiwang_uuid, e)

    @api.model
    def _pull_inbound_red_forms(self):
        """Poll Baiwang for inbound red forms using a sliding catch-up window."""
        companies = self.env['res.company'].search([('l10n_cn_baiwang_subscription_status', '=', 'authorized')])
        today = fields.Date.context_today(self)
        for company in companies:
            latest = self.search([
                ('move_id.company_id', '=', company.id),
                ('baiwang_uuid', '!=', False),
            ], order='create_date desc', limit=1)
            # Start from yesterday (or 30 days ago if brand new)
            start_date = (latest.create_date.date() - timedelta(days=1)) if latest else (today - timedelta(days=30))
            end_date = min(start_date + timedelta(days=30), today)
            client = BaiwangClient(company)
            try:
                res = client.query_red_form_list({
                    'buySelSelector': '1',
                    'entryIdentity': '02',
                    'buyerTaxNo': company.vat,
                    'sellerTaxNo': '',
                    'invoiceStartDate': start_date.strftime('%Y-%m-%d'),
                    'invoiceEndDate': end_date.strftime('%Y-%m-%d'),
                })
                # query_red_form_list already returns the inner list payload.
                form_list = res if isinstance(res, list) else []
                for form in form_list:
                    uuid = form.get('redConfirmUuid')
                    confirm_state = form.get('confirmState')
                    if confirm_state not in ('01', '02', '04'):
                        continue
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
                    is_pending = confirm_state == '02'
                    amt_total = float(form.get('invoiceTotalPrice', 0.0))
                    amt_tax = float(form.get('invoiceTotalTax', 0.0))
                    self.create({
                        'move_id': blue_move.id,
                        'state': 'red_form_pending' if is_pending else 'red_form_confirmed',
                        'baiwang_uuid': uuid,
                        'baiwang_red_form_number': form.get('redConfirmNo'),
                        'baiwang_red_invoice_no': form.get('redInvoiceNo'),
                        'baiwang_confirm_state': confirm_state,
                        'baiwang_red_form_amount_total': amt_total,
                        'baiwang_red_form_amount_tax': amt_tax,
                        'baiwang_red_form_type': form.get('redInvoiceLabel'),
                    })

                    if is_pending:
                        summary = self.env._(
                            "Inbound Red Form %(number)s requires approval (Price: %(price)s, Tax: %(tax)s)",
                            number=form.get('redConfirmNo'),
                            price=amt_total,
                            tax=amt_tax,
                        )
                    else:
                        summary = self.env._("Inbound Red Form %s is approved/issued. Please draft Credit Note.", form.get('redConfirmNo'))

                    blue_move.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=summary,
                        user_id=blue_move.create_uid.id,
                    )
            except Exception as e:  # noqa: BLE001
                _logger.error("Baiwang EDI: Error pulling inbound red forms for company %s: %s", company.name, e)
