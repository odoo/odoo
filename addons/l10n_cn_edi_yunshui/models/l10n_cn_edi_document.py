# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RED_FORM_REASONS = [
    ('01', '01 Invoice Error (开票有误)'),
    ('02', '02 Sales Return (销货退回)'),
    ('03', '03 Service Termination (服务中止)'),
    ('04', '04 Sales Discount (销售折让)'),
]

# The tax bureau's own red form states (hzqrxxzt_dm).
BUREAU_STATES = [
    ('01', '01 No Confirmation Needed (无需确认)'),
    ('02', '02 Seller Entered, Awaiting Buyer (销方录入待购方确认)'),
    ('03', '03 Buyer Entered, Awaiting Seller (购方录入待销方确认)'),
    ('04', '04 Confirmed by Both Parties (购销双方已确认)'),
    ('05', '05 Void: Buyer Refused (作废（销方录入购方否认）)'),
    ('06', '06 Void: Seller Refused (作废（购方录入销方否认）)'),
    ('07', '07 Void: Not Confirmed Within 72 Hours (作废（超72小时未确认）)'),
    ('08', '08 Void: Withdrawn by Initiator (作废（发起方已撤销）)'),
    ('09', '09 Void: Withdrawn After Confirmation (作废（确认后撤销）)'),
    ('10', '10 Void: Abnormal Voucher (作废（异常凭证）)'),
]
BUREAU_STATES_CONFIRMED = {'01', '04'}
BUREAU_STATES_PENDING = {'02', '03'}
RED_FORM_ACTIVE_STATES = ('red_form_pending', 'red_form_confirmed')

# How long after submission a provider may not know a fapiao yet.
SUBMISSION_GRACE = timedelta(minutes=10)


class L10nCnEdiDocument(models.Model):
    """
    What the provider holds for a move: a fapiao we asked it to issue, or a red form.

    Each request gets its own document, the same one for its retries: the serial number
    makes them idempotent. A document dead at the provider is cancelled, and the next
    request of the move gets a new document with a new serial number. Red forms the other
    party raised are documents too, without a serial number.
    """
    _name = 'l10n_cn_edi.document'
    _description = 'E-Fapiao Document'
    _order = 'id desc'

    move_id = fields.Many2one('account.move', string="Journal Entry", required=True, index=True, ondelete='cascade')
    kind = fields.Selection(
        selection=[('fapiao', 'Fapiao'), ('red_form', 'Red Form')],
        required=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('issued', 'Issued'),
        ('red_form_pending', 'Pending Confirmation'),
        ('red_form_confirmed', 'Confirmed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True)
    serial_no = fields.Char(
        string="Serial No",
        readonly=True,
        copy=False,
        index='btree_not_null',
        help="Request serial number sent to the provider; reusing it makes a retry idempotent.",
    )
    sent_date = fields.Datetime(string="Sent On", readonly=True, copy=False)
    sent_data_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Sent Data",
        readonly=True,
        copy=False,
        help="The content Odoo submitted to the provider, for reference.",
    )
    fapiao_no = fields.Char(
        string="Fapiao No.",
        copy=False,
        help="The fapiao issued for this document: the fapiao itself, or the red fapiao of a red form.",
    )
    fapiao_date = fields.Datetime(string="Fapiao Date", copy=False)
    qr_code = fields.Char(string="Fapiao QR Code", readonly=True, copy=False)
    pdf_id = fields.Many2one(comodel_name='ir.attachment', string="Fapiao PDF", readonly=True, copy=False)
    ofd_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Fapiao OFD",
        readonly=True,
        copy=False,
        help="The legal original of the e-Fapiao. The PDF is a copy for reading and emailing.",
    )
    red_form_uuid = fields.Char(string="Red Form UUID", copy=False, index='btree_not_null')
    red_form_number = fields.Char(string="Red Form Number", copy=False)
    bureau_state = fields.Selection(selection=BUREAU_STATES, string="Tax Bureau State", copy=False)
    amount_untaxed = fields.Float(string="Credit Price", copy=False)
    amount_tax = fields.Float(string="Credit Tax", copy=False)
    red_form_reason = fields.Selection(selection=RED_FORM_REASONS, string="Red Form Reason", copy=False)
    error_message = fields.Text(string="Error Details")

    _serial_no_uniq = models.Constraint('UNIQUE(serial_no)', "A serial number can only be sent once.")

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def _l10n_cn_edi_attach_sent_data(self, values):
        """Keep on the move the content about to be submitted under this document's serial number."""
        self.ensure_one()
        raw = json.dumps(values, ensure_ascii=False, indent=2, default=str).encode()
        if self.sent_data_id:
            self.sent_data_id.raw = raw
            return
        self.sent_data_id = self.env['ir.attachment'].create({
            'name': f"{self.serial_no}.json",
            'raw': raw,
            'mimetype': 'application/json',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
        })

    def _l10n_cn_edi_attach_fapiao_files(self, result):
        """Attach the PDF and OFD of a provider result to the move. Return the attachments."""
        self.ensure_one()
        attachments = self.env['ir.attachment']
        for kind, mimetype in (('pdf', 'application/pdf'), ('ofd', 'application/ofd')):
            if result.get(kind):
                attachment = self.env['ir.attachment'].create({
                    'name': result.get(f'{kind}_filename') or f"{self.fapiao_no}.{kind}",
                    'raw': result[kind],
                    'mimetype': mimetype,
                    'res_model': 'account.move',
                    'res_id': self.move_id.id,
                })
                self[f'{kind}_id'] = attachment
                attachments += attachment
        return attachments

    # ------------------------------------------------------------------
    # Fapiao
    # ------------------------------------------------------------------

    def _l10n_cn_edi_set_sent(self, client):
        """Lock the move while the provider holds its fapiao; the cron takes over after the client's follow-ups."""
        self.ensure_one()
        now = fields.Datetime.now()
        self.write({'state': 'sent', 'sent_date': now})
        self.move_id.l10n_cn_edi_state = 'sent'
        self.env.ref('l10n_cn_edi_yunshui.ir_cron_l10n_cn_edi_poll_invoices')._trigger(now + timedelta(seconds=sum(client.result_delays)))

    def _l10n_cn_edi_set_unreachable(self, client, error):
        self._l10n_cn_edi_set_sent(client)
        self.move_id.message_post(body=self.env._(
            "The e-Fapiao provider didn't answer (%(error)s). The fapiao may have been issued: Odoo checks with the provider.",
            error=error,
        ))

    def _l10n_cn_edi_apply_fapiao_result(self, result, client):
        """Record a fapiao result of the provider on this document and its move. Return an error message, or None."""
        self.ensure_one()
        move = self.move_id
        if result.get('state') == 'issued':
            self.write({
                'state': 'issued',
                'fapiao_no': result.get('fapiao_no'),
                'fapiao_date': result.get('fapiao_date'),
                'qr_code': result.get('qr_code'),
                'red_form_uuid': result.get('red_form_uuid'),
                'red_form_number': result.get('red_form_number'),
                'error_message': False,
            })
            move.write({
                'l10n_cn_edi_state': 'issued',
                'l10n_cn_edi_fapiao_no': result.get('fapiao_no'),
                'l10n_cn_edi_fapiao_date': result.get('fapiao_date'),
            })
            move.message_post(
                body=self.env._("E-Fapiao issued successfully. Invoice No: %(fapiao)s", fapiao=result.get('fapiao_no')),
                attachment_ids=self._l10n_cn_edi_attach_fapiao_files(result).ids,
            )
            if warning := move._l10n_cn_edi_build_totals_warning(result):
                move.message_post(body=warning)
            return None
        if result.get('state') == 'sent':
            if self.state != 'sent':
                self._l10n_cn_edi_set_sent(client)
            return None
        error = result.get('error') or self.env._("Unexpected response from the e-Fapiao provider.")
        # A dead order lets the next request use a new document, with a new serial number.
        self.write({'state': 'cancelled' if result.get('new_serial') else 'failed', 'error_message': error})
        move.l10n_cn_edi_state = 'failed'
        move.message_post(body=error)
        return error

    def _l10n_cn_edi_query(self, client, just_submitted=False):
        """Ask the provider for the current result of this document."""
        self.ensure_one()
        if self.kind == 'red_form':
            return client.query_red_form(self)
        return client.query_invoice(self, just_submitted=just_submitted)

    # ------------------------------------------------------------------
    # Red forms
    # ------------------------------------------------------------------

    def _l10n_cn_edi_check_action_role(self, action):
        self.ensure_one()
        move = self.move_id
        if self.state != 'red_form_pending':
            raise UserError(self.env._("Only pending Red Forms can be processed."))
        self.check_access('write')
        if move.move_type not in ('in_invoice', 'out_invoice') or move.state != 'posted':
            raise UserError(self.env._("Only posted bills/invoices can confirm or reject inbound Red Forms."))
        if self.bureau_state not in BUREAU_STATES_PENDING:
            raise UserError(self.env._("This Red Form is no longer waiting for confirmation."))

    @api.model
    def _l10n_cn_edi_state_from_bureau(self, bureau_state, red_fapiao_no):
        if bureau_state in BUREAU_STATES_CONFIRMED:
            # In 数电 the bureau issues the red fapiao once the form is confirmed: until
            # it's out, the credit note has no number to carry, so keep polling.
            return 'red_form_confirmed' if red_fapiao_no else 'red_form_pending'
        if bureau_state in BUREAU_STATES_PENDING:
            return 'red_form_pending'
        return 'cancelled'

    @api.model
    def _cron_check_red_form_status(self):
        """Pull the red forms raised against our fapiao, and poll those still pending."""
        self._l10n_cn_edi_pull_inbound_red_forms()
        pending_docs = self.search([
            ('kind', '=', 'red_form'),
            ('state', '=', 'red_form_pending'),
            ('red_form_uuid', '!=', False),
        ])
        self.env['ir.cron']._commit_progress(remaining=len(pending_docs))
        for company, docs in pending_docs.grouped(lambda doc: doc.move_id.company_id).items():
            try:
                if not company._l10n_cn_edi_is_ready():
                    continue
                client = company._l10n_cn_edi_get_client()
            except UserError as e:
                _logger.warning("E-Fapiao: could not poll the red forms of company %s: %s", company.name, e)
                continue
            for doc in docs:
                try:
                    with self.env.cr.savepoint():
                        doc._l10n_cn_edi_apply_red_form_result(client.query_red_form(doc))
                except UserError as e:
                    _logger.warning("E-Fapiao: could not poll red form %s: %s", doc.red_form_uuid, e)
                if not self.env['ir.cron']._commit_progress(1):
                    return

    def _l10n_cn_edi_apply_red_form_result(self, result):
        """Record a red form result on this document and on the move it belongs to."""
        self.ensure_one()
        bureau_state = result.get('bureau_state')
        if not bureau_state:
            if result.get('error'):
                self.write({'state': 'failed', 'error_message': result['error']})
                self.move_id.message_post(body=self.env._("Red Form rejected: %(error)s", error=result['error']))
            # Otherwise the bureau hasn't registered the form yet: still pending.
            return
        move = self.move_id
        red_fapiao_no = result.get('red_fapiao_no') or self.fapiao_no
        state = self._l10n_cn_edi_state_from_bureau(bureau_state, red_fapiao_no)
        was_state = self.state
        self.write({
            'state': state,
            'bureau_state': bureau_state,
            'red_form_number': result.get('number') or self.red_form_number,
            'fapiao_no': red_fapiao_no,
            'fapiao_date': result.get('red_fapiao_date') or self.fapiao_date,
            'error_message': result.get('error') if state == 'cancelled' else False,
        })
        if state == was_state:
            return
        if state == 'red_form_confirmed':
            move.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=self.env._("Inbound Red Form %(number)s approved and issued. Please ensure a matching Credit Note is posted.", number=self.red_form_number),
                user_id=(move.invoice_user_id or move.create_uid).id,
            )
        elif state == 'cancelled':
            move.message_post(body=self.env._(
                "Red Form rejected/cancelled. Tax bureau state: %(state)s",
                state=dict(BUREAU_STATES).get(bureau_state, bureau_state),
            ))

    @api.model
    def _l10n_cn_edi_pull_inbound_red_forms(self):
        """Poll for red forms raised by suppliers, using a sliding catch-up window."""
        companies = self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'CN')]).filtered(
            lambda company: company._l10n_cn_edi_is_ready(),
        )
        today = fields.Date.context_today(self)
        for company in companies:
            # Keep a monotonically progressing watermark per company.
            start_date = company.l10n_cn_edi_inbound_red_form_last_date or (today - timedelta(days=30))
            end_date = min(start_date + timedelta(days=30), today)
            try:
                with self.env.cr.savepoint():
                    self._l10n_cn_edi_import_inbound_red_forms(company, start_date, end_date)
                    company.sudo().l10n_cn_edi_inbound_red_form_last_date = end_date
            except UserError as e:
                _logger.warning("E-Fapiao: could not pull inbound red forms for company %s: %s", company.name, e)
            self.env['ir.cron']._commit_progress()

    @api.model
    def _l10n_cn_edi_import_inbound_red_forms(self, company, start_date, end_date):
        """
        Track the red forms the other party raised against our fapiao, and tell whoever has to act.

        A supplier's form lands on the vendor bill it reverses, a customer's on the invoice.
        """
        forms = company._l10n_cn_edi_get_client().list_inbound_red_forms(start_date, end_date)
        forms = [
            form for form in forms
            if form.get('uuid') and form.get('bureau_state') in BUREAU_STATES_CONFIRMED | BUREAU_STATES_PENDING
        ]
        if not forms:
            return
        known_uuids = set(self.search([('red_form_uuid', 'in', [form['uuid'] for form in forms])]).mapped('red_form_uuid'))
        bills = self.env['account.move'].search([
            ('l10n_cn_edi_fapiao_no', 'in', [form.get('original_fapiao_no') for form in forms]),
            ('company_id', '=', company.id),
            ('move_type', 'in', ('in_invoice', 'out_invoice')),
        ])
        bill_by_fapiao_no = {bill.l10n_cn_edi_fapiao_no: bill for bill in bills}
        vals_list = []
        for form in forms:
            if form['uuid'] in known_uuids:
                continue
            bill = bill_by_fapiao_no.get(form.get('original_fapiao_no'))
            if not bill:
                _logger.info(
                    "E-Fapiao: inbound red form %s refers to fapiao %s, which matches no invoice or bill of %s",
                    form.get('number'), form.get('original_fapiao_no'), company.name,
                )
                continue
            vals_list.append({
                'move_id': bill.id,
                'kind': 'red_form',
                'state': self._l10n_cn_edi_state_from_bureau(form['bureau_state'], form.get('red_fapiao_no')),
                'red_form_uuid': form['uuid'],
                'red_form_number': form.get('number'),
                'fapiao_no': form.get('red_fapiao_no'),
                'bureau_state': form['bureau_state'],
                'amount_untaxed': form.get('amount_untaxed') or 0.0,
                'amount_tax': form.get('amount_tax') or 0.0,
                'red_form_reason': form.get('reason'),
            })
        for doc in self.create(vals_list):
            if doc.state == 'red_form_pending':
                summary = self.env._(
                    "Inbound Red Form %(number)s requires approval (Price: %(price)s, Tax: %(tax)s)",
                    number=doc.red_form_number,
                    price=doc.amount_untaxed,
                    tax=doc.amount_tax,
                )
            else:
                summary = self.env._("Inbound Red Form %(number)s is approved/issued. Please draft Credit Note.", number=doc.red_form_number)
            # The salesperson rather than the creator, who is OdooBot for an invoice made by a cron.
            doc.move_id.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=summary,
                user_id=(doc.move_id.invoice_user_id or doc.move_id.create_uid).id,
            )
