# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

from .l10n_cn_edi_document import (
    BUREAU_STATES,
    RED_FORM_ACTIVE_STATES,
    RED_FORM_REASONS,
    SUBMISSION_GRACE,
)
from odoo.addons.l10n_cn_edi_yunshui.tools import L10nCnEdiProviderUnreachable
from odoo.addons.phone_validation.tools.phone_validation import phone_format

INVOICE_TYPE_CODES = [
    ('01', '01 Digital Special Invoice (数电专票)'),
    ('02', '02 Digital General Invoice (数电普票)'),
]

EDI_STATES = [
    ('not_sent', 'Not Sent'),
    ('waiting_login', 'Waiting for Login'),
    ('sent', 'Sent'),
    ('issued', 'Issued'),
    ('failed', 'Failed'),
]

_logger = logging.getLogger(__name__)

# The bureau's 发票行性质 (line nature).
LINE_NORMAL, LINE_DISCOUNT, LINE_DISCOUNTED = '0', '1', '2'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_cn_edi_state = fields.Selection(
        selection=EDI_STATES,
        string="E-Fapiao Status",
        default='not_sent',
        copy=False,
    )
    l10n_cn_edi_invoice_type_code = fields.Selection(
        selection=INVOICE_TYPE_CODES,
        string="Fapiao Type",
        default='02',
        required=True,
        help="Type of e-Fapiao to issue: '01' for special (专票) or '02' for general (普票).",
    )
    l10n_cn_edi_fapiao_no = fields.Char(string="Fapiao No.", copy=False, index='btree_not_null')
    l10n_cn_edi_fapiao_date = fields.Datetime(string="Fapiao Date", copy=False)
    l10n_cn_edi_red_form_reason = fields.Selection(
        selection=RED_FORM_REASONS,
        string="Red Form Reason",
        compute='_compute_l10n_cn_edi_red_form_reason',
        store=True,
        readonly=False,
    )
    l10n_cn_edi_document_ids = fields.One2many(
        comodel_name='l10n_cn_edi.document',
        inverse_name='move_id',
        string="E-Fapiao Documents",
    )
    l10n_cn_edi_red_form_required = fields.Boolean(compute='_compute_l10n_cn_edi_red_form_required')
    l10n_cn_edi_date_warning = fields.Char(
        string="Date Consistency Warning",
        compute='_compute_l10n_cn_edi_date_warning',
    )
    l10n_cn_buyer_bank_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Customer Bank Account",
        compute='_compute_l10n_cn_buyer_bank_id',
        store=True,
        readonly=False,
        domain="[('partner_id', '=', commercial_partner_id)]",
        help="The customer's bank account to be printed on the e-Fapiao.",
    )
    l10n_cn_edi_red_form_uuid = fields.Char(
        string="Red Form UUID",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )
    l10n_cn_edi_red_form_number = fields.Char(
        string="Red Form Number",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )
    l10n_cn_edi_red_form_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('red_form_pending', 'Red Form Pending'),
            ('red_form_confirmed', 'Red Form Confirmed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        string="Red Form Status",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )
    l10n_cn_edi_red_form_bureau_state = fields.Selection(
        selection=BUREAU_STATES,
        string="Red Form Tax Bureau State",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )
    l10n_cn_edi_red_form_amount_untaxed = fields.Float(
        string="Inbound Credit Price",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )
    l10n_cn_edi_red_form_amount_tax = fields.Float(
        string="Inbound Credit Tax",
        compute='_compute_l10n_cn_edi_latest_red_form',
        compute_sudo=True,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    @api.depends('l10n_cn_edi_red_form_required')
    def _compute_hide_post_button(self):
        super()._compute_hide_post_button()
        for move in self:
            if move.l10n_cn_edi_red_form_required:
                move.hide_post_button = True

    @api.depends('l10n_cn_edi_document_ids.red_form_reason', 'l10n_cn_edi_document_ids.state')
    def _compute_l10n_cn_edi_red_form_reason(self):
        for move in self:
            latest_doc = move.l10n_cn_edi_document_ids.filtered(
                lambda doc: doc.kind == 'red_form' and doc.state not in ('failed', 'cancelled'),
            ).sorted('id', reverse=True)[:1]
            # Without a red form, the reason is the user's to choose.
            move.l10n_cn_edi_red_form_reason = latest_doc.red_form_reason if latest_doc else move.l10n_cn_edi_red_form_reason

    @api.depends(
        'country_code', 'move_type', 'state', 'l10n_cn_edi_state', 'amount_untaxed', 'amount_tax',
        'reversed_entry_id.l10n_cn_edi_fapiao_no', 'reversed_entry_id.l10n_cn_edi_document_ids.state',
    )
    def _compute_l10n_cn_edi_red_form_required(self):
        for move in self:
            move.l10n_cn_edi_red_form_required = bool(
                move.country_code == 'CN'
                and move.move_type == 'out_refund'
                and move.state == 'draft'
                and move.reversed_entry_id.l10n_cn_edi_fapiao_no
                and move.l10n_cn_edi_state != 'issued'
                # A credit note of a red form the customer raised carries that red fapiao.
                and not move._l10n_cn_edi_matching_inbound_red_form(),
            )

    @api.depends('invoice_date', 'l10n_cn_edi_fapiao_date', 'l10n_cn_edi_fapiao_no', 'l10n_cn_edi_state', 'state', 'move_type', 'country_code')
    def _compute_l10n_cn_edi_date_warning(self):
        today = fields.Date.context_today(self)
        for move in self:
            move.l10n_cn_edi_date_warning = False
            if (
                move.country_code == 'CN'
                and move.move_type == 'out_invoice'
                and move.state == 'posted'
                and move.l10n_cn_edi_state not in ('sent', 'issued')
                and move.invoice_date
                and move.invoice_date != today
            ):
                # The fapiao is dated the day it is issued.
                move.l10n_cn_edi_date_warning = self.env._(
                    "Invoice Date is not today. Please be aware of the consistency between E-fapiao Date and Odoo Invoice Date.",
                )
            elif (
                move.move_type == 'out_refund'
                and move.state == 'draft'
                and move.l10n_cn_edi_fapiao_no
                and move.invoice_date
                and move.l10n_cn_edi_fapiao_date
                and move.invoice_date != move.l10n_cn_edi_fapiao_date.date()
            ):
                move.l10n_cn_edi_date_warning = self.env._(
                    "Invoice Date is different from Fapiao Date. Please be aware of the consistency "
                    "between E-fapiao Date and Odoo Invoice Date.",
                )

    @api.depends('commercial_partner_id')
    def _compute_l10n_cn_buyer_bank_id(self):
        for move in self:
            move.l10n_cn_buyer_bank_id = move.commercial_partner_id.bank_ids[:1]

    @api.depends(
        'l10n_cn_edi_document_ids.kind',
        'l10n_cn_edi_document_ids.state',
        'l10n_cn_edi_document_ids.bureau_state',
        'l10n_cn_edi_document_ids.red_form_uuid',
        'l10n_cn_edi_document_ids.red_form_number',
        'l10n_cn_edi_document_ids.amount_untaxed',
        'l10n_cn_edi_document_ids.amount_tax',
    )
    def _compute_l10n_cn_edi_latest_red_form(self):
        for move in self:
            # A red fapiao of our own carries the red form the bureau recorded for it.
            latest = move.l10n_cn_edi_document_ids.filtered(
                lambda doc: doc.kind == 'red_form' or doc.red_form_uuid,
            ).sorted('id', reverse=True)[:1]
            move.l10n_cn_edi_red_form_uuid = latest.red_form_uuid
            move.l10n_cn_edi_red_form_number = latest.red_form_number
            move.l10n_cn_edi_red_form_status = latest.state if latest.kind == 'red_form' else False
            move.l10n_cn_edi_red_form_bureau_state = latest.bureau_state
            move.l10n_cn_edi_red_form_amount_untaxed = latest.amount_untaxed
            move.l10n_cn_edi_red_form_amount_tax = latest.amount_tax

    # ------------------------------------------------------------------
    # CRUD and lifecycle guards
    # ------------------------------------------------------------------

    def _l10n_cn_edi_has_active_red_form(self):
        self.ensure_one()
        return any(doc.state in RED_FORM_ACTIVE_STATES for doc in self.l10n_cn_edi_document_ids)

    def _l10n_cn_edi_check_red_lock(self):
        """Refuse to change a draft credit note whose red fapiao is requested or issued."""
        if any(
            move.move_type == 'out_refund'
            and move.state == 'draft'
            and (move.l10n_cn_edi_state in ('sent', 'issued') or move._l10n_cn_edi_has_active_red_form())
            for move in self
        ):
            raise UserError(self.env._("You cannot modify this Credit Note: its red fapiao is requested or issued."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active_red_forms(self):
        for move in self:
            if move._l10n_cn_edi_has_active_red_form():
                raise UserError(self.env._("Cannot delete a record with a pending or confirmed Red Form."))
            if (
                move.move_type == 'out_refund'
                and move.state == 'draft'
                and move.l10n_cn_edi_state in ('sent', 'issued')
            ):
                raise UserError(self.env._("Cannot delete a Credit Note whose e-Fapiao is pending or issued."))

    def write(self, vals):
        protected_fields = {
            'invoice_line_ids', 'line_ids', 'partner_id', 'l10n_cn_edi_invoice_type_code', 'l10n_cn_buyer_bank_id',
            'invoice_date', 'currency_id', 'narration',
        }
        if protected_fields & vals.keys():
            self._l10n_cn_edi_check_red_lock()
        return super().write(vals)

    def _post(self, soft=True):
        # EXTENDS 'account'
        for move in self.filtered(lambda move: move.move_type == 'out_refund' and move.l10n_cn_edi_state != 'issued'):
            if doc := move._l10n_cn_edi_matching_inbound_red_form():
                move._l10n_cn_edi_carry_red_form(doc)
        for move in self.filtered(lambda move: move.move_type == 'out_refund'):
            if move.l10n_cn_edi_red_form_required:
                raise UserError(self.env._("This Credit Note can be posted only once its red fapiao is issued."))
            if move._l10n_cn_edi_red_amount_mismatch():
                raise UserError(self.env._(
                    "This Credit Note no longer credits the amount of its red fapiao %(fapiao)s.",
                    fapiao=move.l10n_cn_edi_fapiao_no or move.l10n_cn_edi_red_form_number,
                ))
        return super()._post(soft=soft)

    def button_cancel(self):
        # EXTENDS 'account'
        if any(move.l10n_cn_edi_state in ('sent', 'issued') or move._l10n_cn_edi_has_active_red_form() for move in self):
            raise UserError(self.env._("You cannot cancel a document whose e-Fapiao or Red Form is pending or already issued."))
        return super().button_cancel()

    def button_draft(self):
        # EXTENDS 'account'
        if any(move.l10n_cn_edi_state in ('sent', 'issued') or move._l10n_cn_edi_has_active_red_form() for move in self):
            raise UserError(self.env._(
                "You cannot reset this document to draft because its e-Fapiao or Red Form is pending or already issued. "
                "You must issue a Red Form (Credit Note) to reverse it.",
            ))
        return super().button_draft()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # EXTENDS 'account'
        reversals = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        for reversal in reversals.filtered(lambda move: move.l10n_cn_edi_state != 'issued'):
            doc = reversal._l10n_cn_edi_inbound_red_form()
            if not doc:
                continue
            if reversal._l10n_cn_edi_matches_red_form(doc):
                reversal._l10n_cn_edi_carry_red_form(doc)
            else:
                reversal.message_post(body=self.env._(
                    "Red Form %(number)s credits %(untaxed)s (tax %(tax)s), not the amounts of this Credit Note: "
                    "a Credit Note of exactly that amount carries its red fapiao %(red_fapiao)s.",
                    number=doc.red_form_number,
                    untaxed=abs(doc.amount_untaxed),
                    tax=abs(doc.amount_tax),
                    red_fapiao=doc.fapiao_no,
                ))
        return reversals

    # ------------------------------------------------------------------
    # Red forms the other party raised
    # ------------------------------------------------------------------

    def _l10n_cn_edi_inbound_red_form(self):
        """
        The confirmed red form the other party raised on this credit note's invoice, unless
        another credit note already carries its red fapiao."""
        self.ensure_one()
        invoice = self.reversed_entry_id
        if invoice.move_type not in ('in_invoice', 'out_invoice'):
            return self.env['l10n_cn_edi.document']
        carried = set((invoice.reversal_move_ids - self._origin).mapped('l10n_cn_edi_fapiao_no'))
        return invoice.l10n_cn_edi_document_ids.filtered(
            lambda doc: doc.state == 'red_form_confirmed' and doc.fapiao_no not in carried,
        )[:1]

    def _l10n_cn_edi_matches_red_form(self, doc):
        """Whether this credit note credits what the customer's red form ``doc`` reverses."""
        self.ensure_one()
        if self.move_type != 'out_refund' or not (doc.amount_untaxed or doc.amount_tax):
            return True
        return not (
            self.currency_id.compare_amounts(abs(doc.amount_untaxed), self.amount_untaxed)
            or self.currency_id.compare_amounts(abs(doc.amount_tax), self.amount_tax)
        )

    def _l10n_cn_edi_matching_inbound_red_form(self):
        self.ensure_one()
        doc = self._l10n_cn_edi_inbound_red_form()
        return doc if doc and self._l10n_cn_edi_matches_red_form(doc) else doc.browse()

    def _l10n_cn_edi_carry_red_form(self, doc):
        self.write({
            'l10n_cn_edi_fapiao_no': doc.fapiao_no,
            'l10n_cn_edi_state': 'issued',
            'l10n_cn_edi_red_form_reason': doc.red_form_reason,
        })

    def _l10n_cn_edi_red_amount_mismatch(self):
        """Whether this credit note credits another amount than the red fapiao it carries or awaits."""
        self.ensure_one()
        doc = (
            self.l10n_cn_edi_document_ids.filtered(lambda doc: doc.state in RED_FORM_ACTIVE_STATES)[:1]
            or self.reversed_entry_id.l10n_cn_edi_document_ids.filtered(
                lambda doc: doc.fapiao_no and doc.fapiao_no == self.l10n_cn_edi_fapiao_no,
            )[:1]
        )
        if doc.amount_untaxed or doc.amount_tax:
            return not self._l10n_cn_edi_matches_red_form(doc)
        if self.l10n_cn_edi_state in ('sent', 'issued') and self.reversed_entry_id:
            # A red fapiao of our own reverses the whole invoice.
            return bool(self.currency_id.compare_amounts(self.amount_total, self.reversed_entry_id.amount_total))
        return False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_l10n_cn_edi_request_red_form(self):
        """Request a red letter confirmation form for a draft credit note of an issued invoice."""
        self.ensure_one()
        self.check_access('write')
        if self.move_type != 'out_refund':
            raise UserError(self.env._("Red Form can only be requested for Credit Notes."))
        if self.state != 'draft':
            raise UserError(self.env._("Credit Note must be in draft before requesting a Red Form."))
        # Read before touching the documents: they drive the reason's compute.
        reason = self.l10n_cn_edi_red_form_reason
        if not reason:
            raise UserError(self.env._("Please select a Red Form Reason before requesting."))
        if self.l10n_cn_edi_state in ('sent', 'issued'):
            raise UserError(self.env._("Cannot request a Red Form for an invoice in 'sent' or 'issued' state."))
        original_move = self.reversed_entry_id
        if not original_move.l10n_cn_edi_fapiao_no:
            raise UserError(self.env._("Cannot find the original fapiao number. Ensure this credit note was created from an issued e-Fapiao."))
        if inbound := original_move.l10n_cn_edi_document_ids.filtered(lambda doc: doc.state in RED_FORM_ACTIVE_STATES)[:1]:
            raise UserError(self.env._(
                "The customer raised Red Form %(number)s against fapiao %(fapiao)s: credit the invoice through that Red Form.",
                number=inbound.red_form_number,
                fapiao=original_move.l10n_cn_edi_fapiao_no,
            ))
        if (original_move.reversal_move_ids - self).filtered(
            lambda move: move.l10n_cn_edi_state in ('sent', 'issued') or move._l10n_cn_edi_has_active_red_form(),
        ):
            raise UserError(self.env._(
                "Another Credit Note already requested or carries the red fapiao of %(fapiao)s.",
                fapiao=original_move.l10n_cn_edi_fapiao_no,
            ))
        if self.currency_id.compare_amounts(self.amount_total, original_move.amount_total):
            raise UserError(self.env._(
                "A red fapiao can only reverse the whole fapiao %(fapiao)s (%(amount)s). "
                "Credit the full amount, then issue a new invoice with the right amounts.",
                fapiao=original_move.l10n_cn_edi_fapiao_no,
                amount=original_move.amount_total,
            ))
        client = self.company_id._l10n_cn_edi_get_client()
        client.ensure_ready()
        return self._l10n_cn_edi_request_direct_red(client, original_move)

    def _l10n_cn_edi_request_direct_red(self, client, original_move):
        """Issue the red fapiao of this credit note directly, without a red form."""
        self.ensure_one()
        doc = self._l10n_cn_edi_get_document('fapiao')
        values = self._l10n_cn_edi_prepare_red_form_values(original_move, doc)
        doc._l10n_cn_edi_attach_sent_data(values)
        try:
            result = client.issue_direct_red(values)
        except L10nCnEdiProviderUnreachable as e:
            doc._l10n_cn_edi_set_unreachable(client, e)
            return None
        except UserError as e:
            # Not raised: that would also roll back what the provider recorded, like a forced relogin.
            self.message_post(body=self.env._("Red fapiao not issued: %(error)s", error=e))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {'type': 'danger', 'message': str(e)},
            }
        if doc._l10n_cn_edi_apply_fapiao_result(result, client) or result.get('state') != 'sent':
            return None
        for delay in client.result_delays:
            client.wait(delay)
            try:
                polled = client.query_invoice(doc, just_submitted=True)
            except UserError as e:
                _logger.warning("E-Fapiao: could not follow up on direct red invoice %s: %s", self.name, e)
                continue
            if doc._l10n_cn_edi_apply_fapiao_result(polled, client) or polled.get('state') != 'sent':
                break
        return None

    def action_l10n_cn_edi_login(self):
        """Log the drawer back in to the tax bureau, then send this invoice again."""
        self.ensure_one()
        self.check_access('write')
        return self.company_id._l10n_cn_edi_action_login(self)

    def action_l10n_cn_edi_approve_inbound_red_form(self):
        """Approve a red form the other party raised against this vendor bill or invoice."""
        self.ensure_one()
        self.check_access('write')
        doc = self.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending')[:1]
        if not doc:
            return
        doc._l10n_cn_edi_check_action_role('confirm')
        try:
            self.company_id._l10n_cn_edi_get_client().operate_red_form(doc, 'confirm')
        except UserError as e:
            raise UserError(self.env._("Failed to approve the Red Form: %(error)s", error=e))
        # The bureau issues the red fapiao now; the cron picks up its number.
        doc._l10n_cn_edi_apply_red_form_result({'bureau_state': '04'})
        self.message_post(body=self.env._("Inbound Red Form approved. The tax bureau now issues the red fapiao."))

    def action_l10n_cn_edi_reject_inbound_red_form(self):
        """Refuse a red form the other party raised against this vendor bill or invoice."""
        self.ensure_one()
        self.check_access('write')
        doc = self.l10n_cn_edi_document_ids.filtered(lambda d: d.state == 'red_form_pending')[:1]
        if not doc:
            return
        doc._l10n_cn_edi_check_action_role('reject')
        try:
            self.company_id._l10n_cn_edi_get_client().operate_red_form(doc, 'reject')
        except UserError as e:
            raise UserError(self.env._("Failed to reject the Red Form: %(error)s", error=e))
        # 05: the buyer refused the seller's form; 06: the seller refused the buyer's.
        bureau_state = '06' if self.move_type == 'out_invoice' else '05'
        doc.write({'state': 'cancelled', 'bureau_state': bureau_state, 'error_message': self.env._("Rejected by user.")})
        self.message_post(body=self.env._("Inbound Red Form %(number)s rejected.", number=doc.red_form_number))

    # ------------------------------------------------------------------
    # Blue fapiao issuance
    # ------------------------------------------------------------------

    def _l10n_cn_edi_submit_invoice(self, client):
        """Submit the e-Fapiao of this customer invoice. Return an error message, or None."""
        self.ensure_one()
        if self.l10n_cn_edi_state in ('sent', 'issued'):
            return None
        doc = self._l10n_cn_edi_get_document('fapiao')
        try:
            values = self._l10n_cn_edi_prepare_invoice_values(doc)
            doc._l10n_cn_edi_attach_sent_data(values)
            result = client.issue_invoice(values)
        except L10nCnEdiProviderUnreachable as e:
            doc._l10n_cn_edi_set_unreachable(client, e)
            return None
        except UserError as e:
            # Nothing was submitted: leave the invoice retryable.
            return str(e)
        return doc._l10n_cn_edi_apply_fapiao_result(result, client)

    def _l10n_cn_edi_fetch_submitted(self, client):
        """
        Follow up on fapiao just submitted, once per delay of the client; the cron takes over after.

        Return ``{move: error message}`` for those that failed meanwhile.
        """
        errors = {}
        for delay in client.result_delays:
            pending = self.l10n_cn_edi_document_ids.filtered(lambda doc: doc.kind == 'fapiao' and doc.state == 'sent')
            if not pending:
                break
            client.wait(delay)
            for doc in pending:
                try:
                    result = client.query_invoice(doc, just_submitted=True)
                except UserError as e:
                    _logger.warning("E-Fapiao: could not follow up on invoice %s: %s", doc.move_id.name, e)
                    continue
                if error := doc._l10n_cn_edi_apply_fapiao_result(result, client):
                    errors[doc.move_id] = error
        return errors

    def _l10n_cn_edi_build_totals_warning(self, result):
        """Warn when the provider issued other amounts than the move's, e.g. content edited under a reused serial."""
        self.ensure_one()
        amounts = self._l10n_cn_edi_amounts()
        if not any(
            result.get(key) is not None and self.currency_id.compare_amounts(abs(result[key]), abs(amount))
            for key, amount in amounts.items()
        ):
            return False
        return self.env._(
            "E-Fapiao amount mismatch: the provider issued %(provider)s (untaxed/tax/total), Odoo has %(odoo)s. "
            "Please review this document manually.",
            provider=" / ".join(str(abs(result[key])) if result.get(key) is not None else "-" for key in amounts),
            odoo=" / ".join(str(abs(amount)) for amount in amounts.values()),
        )

    def _l10n_cn_edi_issued_document(self):
        """Return the document of the fapiao Odoo issued for this move, if any."""
        self.ensure_one()
        return self.l10n_cn_edi_document_ids.filtered(
            lambda doc: doc.serial_no and doc.state in ('issued', 'red_form_confirmed'),
        ).sorted('id', reverse=True)[:1]

    def action_l10n_cn_edi_fetch_fapiao_files(self):
        """
        Download again the PDF and OFD that issued fapiao are missing, e.g. after a failed download.

        Each move logs its outcome in its chatter: one that fails must not undo the others.
        """
        self.check_access('write')
        docs = self.env['l10n_cn_edi.document'].union(*(move._l10n_cn_edi_issued_document() for move in self))
        docs = docs.filtered(lambda doc: not (doc.pdf_id and doc.ofd_id))
        failed = self.env['account.move']
        for company, company_docs in docs.grouped(lambda doc: doc.move_id.company_id).items():
            client = company._l10n_cn_edi_get_client()
            for doc in company_docs:
                try:
                    result = doc._l10n_cn_edi_query(client)
                except UserError as e:
                    result = {'error': str(e)}
                missing = {kind: result[kind] for kind in ('pdf', 'ofd') if result.get(kind) and not doc[f'{kind}_id']}
                if attachments := doc._l10n_cn_edi_attach_fapiao_files(missing):
                    doc.move_id.message_post(body=self.env._("E-Fapiao files downloaded."), attachment_ids=attachments.ids)
                else:
                    failed += doc.move_id
                    doc.move_id.message_post(body=self.env._(
                        "The e-Fapiao files could not be downloaded: %(error)s",
                        error=result.get('error') or self.env._("the provider has none for this fapiao yet."),
                    ))
        if not failed:
            return None
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'warning',
                'message': self.env._(
                    "Some e-Fapiao files could not be downloaded: %(moves)s. See their chatter.",
                    moves=', '.join(failed.mapped('name')),
                ),
            },
        }

    @api.model
    def _cron_l10n_cn_edi_poll_invoices(self):
        """Fetch the result of every fapiao the provider accepted but hadn't finished issuing."""
        docs = self.env['l10n_cn_edi.document'].search([('kind', '=', 'fapiao'), ('state', '=', 'sent')])
        self.env['ir.cron']._commit_progress(remaining=len(docs))
        grace_start = fields.Datetime.now() - SUBMISSION_GRACE
        for company, company_docs in docs.grouped(lambda doc: doc.move_id.company_id).items():
            try:
                if not company._l10n_cn_edi_is_ready():
                    continue
                client = company._l10n_cn_edi_get_client()
            except UserError as e:
                _logger.warning("E-Fapiao: could not poll the fapiao of company %s: %s", company.name, e)
                continue
            for doc in company_docs:
                just_submitted = bool(doc.sent_date and doc.sent_date > grace_start)
                try:
                    with self.env.cr.savepoint():
                        doc._l10n_cn_edi_apply_fapiao_result(doc._l10n_cn_edi_query(client, just_submitted), client)
                except UserError as e:
                    _logger.warning("E-Fapiao: could not poll invoice %s: %s", doc.move_id.name, e)
                if not self.env['ir.cron']._commit_progress(1):
                    return

    # ------------------------------------------------------------------
    # Serial numbers
    # ------------------------------------------------------------------

    def _l10n_cn_edi_get_document(self, kind):
        """
        Return the document to send this move's ``kind`` request with.

        That's the move's latest one, retried under the same serial number, unless the
        provider's order is dead: the next attempt then gets a new document.
        """
        self.ensure_one()
        sent = self.l10n_cn_edi_document_ids.filtered(lambda doc: doc.kind == kind and doc.serial_no).sorted('id', reverse=True)
        if sent and sent[0].state != 'cancelled':
            return sent[0]
        return self.env['l10n_cn_edi.document'].create({
            'move_id': self.id,
            'kind': kind,
            'serial_no': self._l10n_cn_edi_make_serial(attempt=len(sent)),
        })

    def _l10n_cn_edi_make_serial(self, attempt):
        """
        Return the serial number of this move's ``attempt``-th request.

        The same move and attempt always give the same serial, so a retry after a lost
        answer or a rolled back transaction can't issue a second fapiao.

        The hashed database uuid keeps the copies of a database that share a provider
        account apart. Providers take 20 characters at most.
        """
        self.ensure_one()
        prefix = 'R' if self.move_type == 'out_refund' else 'B'
        db_uuid = self.env['ir.config_parameter'].sudo().get_str('database.uuid')
        db_hash = hashlib.sha1(db_uuid.encode(), usedforsecurity=False).hexdigest().upper()
        return f"{prefix}{self.id}_{attempt}_{db_hash}"[:20]

    # ------------------------------------------------------------------
    # Fapiao content
    # ------------------------------------------------------------------

    def _l10n_cn_edi_amounts(self):
        self.ensure_one()
        return {
            'amount_untaxed': round(sum(self._l10n_cn_edi_product_lines().mapped('price_subtotal')), 2),
            'amount_tax': round(self.amount_tax, 2),
            'amount_total': round(self.amount_total, 2),
        }

    def _l10n_cn_edi_prepare_invoice_values(self, document):
        """Return the content of this invoice's fapiao, sent with ``document``."""
        self.ensure_one()
        partner = self.partner_id
        remark = str(self.narration) if self.narration else ''
        buyer_phone = False
        if partner.phone:
            formatted_phone = phone_format(
                partner.phone,
                partner.country_id.code,
                partner.country_id.phone_code,
                force_format='E164',
                raise_exception=False,
            ) or ''
            if formatted_phone.startswith('+86'):
                buyer_phone = formatted_phone[3:]
            else:
                # The fapiao only has room for a mainland number; keep the others readable in the remark.
                remark = f"{remark} | Phone: {partner.phone}".strip(' |')
        bank = self.l10n_cn_buyer_bank_id
        return {
            'serial_no': document.serial_no,
            'invoice_type_code': self.l10n_cn_edi_invoice_type_code,
            # The buyer is the legal entity; the address and phone are the invoiced contact's.
            'buyer_name': self.commercial_partner_id.name or '',
            'buyer_tax_no': self.commercial_partner_id.vat or '',
            'buyer_is_natural_person': not self.commercial_partner_id.vat,
            'buyer_address': ' '.join(filter(None, [partner.street, partner.street2, partner.city])),
            'buyer_phone': buyer_phone,
            'buyer_email': partner.email or '',
            # The fapiao prints bank and account on one line (开户行及账号).
            'buyer_bank': f"{bank.bank_name or ''} {bank.account_number or ''}".strip(),
            # For providers that take them apart.
            'buyer_bank_name': bank.bank_name or '',
            'buyer_bank_account': bank.account_number or '',
            'drawer': self.company_id.l10n_cn_edi_drawer or self.env.user.name,
            'remark': remark,
            **self._l10n_cn_edi_amounts(),
            'lines': self._l10n_cn_edi_prepare_lines(),
        }

    def _l10n_cn_edi_product_lines(self):
        return self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')

    def _l10n_cn_edi_prepare_lines(self):
        """
        Fapiao lines, with negative lines spread proportionally over the others as discount lines.

        The bureau has no negative line: a discount is a 折扣行 (nature '1') right after the
        被折扣行 (nature '2') it reduces.
        """
        product_lines = self._l10n_cn_edi_product_lines()
        for line in product_lines:
            if len(line.tax_ids) > 1 or line.tax_ids.filtered(lambda tax: tax.amount_type != 'percent'):
                raise UserError(self.env._(
                    "Only one percentage tax is supported per line for e-Fapiao: %(line)s",
                    line=line.name,
                ))
        positive_lines = product_lines.filtered(lambda line: line.price_subtotal >= 0)
        negative_lines = product_lines - positive_lines
        if negative_lines and len({(line.tax_ids.amount, line.tax_ids.price_include) for line in product_lines}) > 1:
            raise UserError(self.env._(
                "Global negative lines spanning multiple tax groups are not supported for e-Fapiao. "
                "Please split by tax group before issuing.",
            ))
        total_discount = sum(negative_lines.mapped('price_subtotal'))
        total_discount_tax = sum(line.price_total - line.price_subtotal for line in negative_lines)
        total_positive = sum(positive_lines.mapped('price_subtotal'))
        remaining_discount, remaining_discount_tax = total_discount, total_discount_tax
        lines = []
        for index, line in enumerate(positive_lines):
            if not line.l10n_cn_tax_category_id:
                raise UserError(self.env._("Missing Tax Category Code on line: %(line)s", line=line.name))
            amount = round(line.price_subtotal, 2)
            tax = round(line.price_total - line.price_subtotal, 2)
            tax_record = line.tax_ids
            discount, discount_tax = 0.0, 0.0
            if total_discount < 0 and total_positive > 0:
                if index == len(positive_lines) - 1:
                    discount, discount_tax = round(remaining_discount, 2), round(remaining_discount_tax, 2)
                else:
                    ratio = amount / total_positive
                    discount, discount_tax = round(total_discount * ratio, 2), round(total_discount_tax * ratio, 2)
                    remaining_discount -= discount
                    remaining_discount_tax -= discount_tax
            if line.discount:
                if line.discount >= 100:
                    raise UserError(self.env._(
                        "100% line discounts are not supported for e-Fapiao. Use an explicit negative line instead.",
                    ))
                factor = line.discount / 100.0
                gross, gross_tax = round(amount / (1.0 - factor), 2), round(tax / (1.0 - factor), 2)
                discount += amount - gross
                discount_tax += tax - gross_tax
                amount, tax = gross, gross_tax
            is_discounted = discount < 0
            line_values = {
                'price_include': tax_record.price_include,
                'line_no': len(lines) + 1,
                'nature': LINE_DISCOUNTED if is_discounted else LINE_NORMAL,
                'name': (line.name or line.product_id.name or '').replace('\n', ' ')[:100],
                'tax_category_code': line.l10n_cn_tax_category_id.code,
                'tax_rate': abs(tax_record.amount) / 100.0,
                'amount_untaxed': amount,
                'amount_tax': tax,
                'amount_total': round(amount + tax, 2),
                'quantity': line.quantity or False,
                'unit_price': round(amount / line.quantity, 8) if line.quantity else round(line.price_unit, 8),
                'uom': line.product_uom_id.name or '',
                'vat_special_policy': tax_record.l10n_cn_vat_special_policy or False,
                'free_tax_mark': tax_record.l10n_cn_free_tax_mark or False,
                'reduced_tax_code': tax_record.l10n_cn_reduced_tax_code or False,
            }
            lines.append(line_values)
            if is_discounted:
                lines.append({
                    **line_values,
                    'line_no': len(lines) + 1,
                    'nature': LINE_DISCOUNT,
                    'amount_untaxed': round(discount, 2),
                    'amount_tax': round(discount_tax, 2),
                    'amount_total': round(discount + discount_tax, 2),
                    'quantity': False,
                    'unit_price': False,
                    'uom': '',
                })
        return lines

    # ------------------------------------------------------------------
    # Red forms
    # ------------------------------------------------------------------

    def _l10n_cn_edi_prepare_red_form_values(self, original_move, document):
        """Return the content of this credit note's red fapiao, sent with ``document``."""
        self.ensure_one()
        amounts = self._l10n_cn_edi_amounts()
        original_amounts = original_move._l10n_cn_edi_amounts()
        return {
            'serial_no': document.serial_no,
            'reason': self.l10n_cn_edi_red_form_reason,
            'seller_name': self.company_id.name,
            # Same buyer as the original fapiao: the legal entity, not the invoiced contact.
            'buyer_name': self.commercial_partner_id.name or '',
            'buyer_tax_no': self.commercial_partner_id.vat or '',
            'buyer_email': self.partner_id.email or '',
            'original_fapiao_no': original_move.l10n_cn_edi_fapiao_no,
            'original_fapiao_date': original_move.l10n_cn_edi_fapiao_date or original_move.invoice_date,
            'original_invoice_type_code': original_move.l10n_cn_edi_invoice_type_code,
            'original_amount_untaxed': original_amounts['amount_untaxed'],
            'original_amount_tax': original_amounts['amount_tax'],
            'amount_untaxed': -abs(amounts['amount_untaxed']),
            'amount_tax': -abs(amounts['amount_tax']),
            'lines': self._l10n_cn_edi_prepare_red_form_lines(),
        }

    def _l10n_cn_edi_prepare_red_form_lines(self):
        """
        Red form lines: discounts netted into the line they reduce, every amount negative.

        ``original_line_no`` points at the line of the original fapiao being credited, which
        assumes the credit note keeps the original invoice's line order.
        """
        red_lines = []
        for line in self._l10n_cn_edi_prepare_lines():
            if line['nature'] == LINE_DISCOUNT:
                parent = red_lines[-1]
                parent['amount_untaxed'] = round(parent['amount_untaxed'] + line['amount_untaxed'], 2)
                parent['amount_tax'] = round(parent['amount_tax'] + line['amount_tax'], 2)
                parent['amount_total'] = round(parent['amount_total'] + line['amount_total'], 2)
                if parent.get('quantity'):
                    parent['unit_price'] = round(parent['amount_untaxed'] / parent['quantity'], 8)
                parent['nature'] = LINE_NORMAL
                continue
            red_lines.append({**line, 'original_line_no': line['line_no']})
        for line in red_lines:
            line['amount_untaxed'] = -abs(line['amount_untaxed'])
            line['amount_tax'] = -abs(line['amount_tax'])
            line['amount_total'] = -abs(line['amount_total'])
            if line['quantity']:
                line['quantity'] = -abs(line['quantity'])
        return red_lines
