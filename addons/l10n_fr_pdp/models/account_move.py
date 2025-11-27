import re
from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import frozendict, html2plaintext

from odoo.addons.l10n_fr_pdp.models.account_edi_proxy_user import STATUS_TO_PROCESS_CONDITION_CODE_PDP
from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID
from odoo.addons.l10n_fr_pdp.models.account_peppol_response import NEW_STATUSES
from odoo.addons.l10n_fr_pdp.models.pdp_flow import FLOW_OPEN_STATES_SELECTION, FLOW_SENT_STATES, FLOW_SENT_STATES_SELECTION
from odoo.addons.l10n_fr_pdp.utils import drom_com_territories

PAID_CODES = frozenset({'ESC', 'RAB', 'REM', 'MPA', 'MEN'})
G1_05_RE = re.compile(r'^(?! )(?!.*  )[A-Za-z0-9+\-_/ ]{1,20}(?<! )$')  # can't start with space, can't have 2 consecutive spaces, max 20 chars, allowed chars are alphanumeric, space, -, _, /, can't end with space


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_move_state = fields.Selection(
        string="E-Invoicing Status",
        selection_add=[
            ('PD', "With Payments"),
            *[(status, lt._source) for status, lt in NEW_STATUSES.items()],
        ],
    )
    pdp_ppf_move_state = fields.Selection(
        selection=[
            ('in_progress', 'In Progress'),
            ('sent', 'Sent'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_pdp_ppf_state',
        store=True,
        string='PPF Invoice Status',
        copy=False,
    )
    pdp_lifecycle_residual = fields.Monetary(
        string='Lifecycle Residual',
        compute='_compute_pdp_lifecycle_residual',
        store=True,
        copy=False,
        help="Technical field indicating the amount of collected money we have still to report to the PPF via a lifecycle."
    )
    pdp_ppf_lifecycle_state = fields.Selection(
        selection=[
            ('in_progress', 'In Progress'),
            ('sent', 'Sent'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_pdp_ppf_state',
        store=True,
        string='PPF Lifeycle Status',
        copy=False,
    )
    pdp_can_send_response = fields.Boolean(compute='_compute_pdp_can_send_response')
    pdp_is_sent = fields.Boolean(compute='_compute_pdp_is_sent')
    pdp_uses_pdp = fields.Boolean(compute='_compute_pdp_uses_pdp')
    l10n_fr_pdp_sent_in_flow_ids = fields.Many2many(
        comodel_name='l10n.fr.pdp.reports.flow',
        string="Sent in PDP Flows",
        relation='sent_account_move__pdp_flow',
        column1='move_id',
        column2='flow_id',
        copy=False,
    )
    l10n_fr_pdp_last_flow_id = fields.Many2one(
        comodel_name='l10n.fr.pdp.reports.flow',
        string="Last PDP Flow",
        compute='_compute_l10n_fr_pdp_last_flow_id',
        store=True,
        copy=False,
    )
    l10n_fr_pdp_status = fields.Selection(
        selection=[
            ('out_of_scope', "Out of scope"),
            ('pending', "Pending"),
            ('error', "Error"),
        ] + FLOW_OPEN_STATES_SELECTION + FLOW_SENT_STATES_SELECTION,
        string="E-Reporting Status",
        compute='_compute_l10n_fr_pdp_status',
        store=True,
        copy=False,
    )
    l10n_fr_pdp_display_info = fields.Boolean(related='company_id.l10n_fr_f10_enable_reporting')
    l10n_fr_pdp_flow_10_report_type = fields.Selection(  # This field dictates if a move has to be reported or not.
        selection=[('transaction', 'Transaction'), ('payment', 'Payment')],
        compute='_compute_l10n_fr_pdp_flow_10_report_type',
        store=True,
        copy=False,
    )
    l10n_fr_pdp_flow_10_operation_type = fields.Selection(
        selection=[('sale', 'Sale'), ('purchase', 'Purchase')],
        compute='_compute_l10n_fr_pdp_flow_10_operation_type',
        store=True,
        copy=False,
    )
    l10n_fr_pdp_error_message = fields.Text(
        string="Flow 10 blocking errors",
        compute='_compute_l10n_fr_pdp_error_message',
    )
    l10n_fr_pdp_has_error = fields.Boolean(
        compute='_compute_l10n_fr_pdp_has_error',
        store=True,
        readonly=True,
        copy=False,
    )

    @api.depends('peppol_is_sent', 'l10n_fr_pdp_sent_in_flow_ids')
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account' to hide the reset to draft button for sent PDP invoices
        super()._compute_show_reset_to_draft_button()
        relevant_moves = self.filtered(
            lambda move: move.l10n_fr_pdp_sent_in_flow_ids or move.pdp_is_sent and move.is_sale_document(include_receipts=True)
        )
        relevant_moves.show_reset_to_draft_button = False

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id',
        'line_ids.matched_credit_ids.credit_move_id',
        'peppol_message_uuid',
        'peppol_response_ids',
        'pdp_ppf_move_state',
        'payment_state',
    )
    def _compute_pdp_lifecycle_residual(self):
        for move in self:
            already_sent = move._pdp_get_paid_lifecycle_total_amount()
            is_relevant = already_sent or (
                (move.pdp_ppf_move_state in ['sent', 'done'] or move.pdp_is_sent)
                and move.is_sale_document(include_receipts=True)
                and move.payment_state in ['paid', 'partial']
                and move.currency_id.name == 'EUR'
            )
            amount = 0
            if is_relevant:
                amount = move._pdp_get_paid_amount() - already_sent
            move.pdp_lifecycle_residual = amount

    @api.depends('peppol_response_ids', 'peppol_response_ids.peppol_state')
    def _compute_peppol_move_state(self):
        super()._compute_peppol_move_state()
        for move in self:
            # Handle sale and purchase documents in case we sent / received the document.
            if move.peppol_move_state != 'error' and (response_status := move._pdp_get_response_status()):
                move.peppol_move_state = response_status

    @api.depends('peppol_response_ids', 'peppol_response_ids.peppol_state', 'peppol_response_ids.response_code')
    def _compute_pdp_ppf_state(self):
        for move in self:
            processed = move.peppol_move_state and move.peppol_move_state not in ('ready', 'to_send', 'processing', 'error')
            move.pdp_ppf_move_state = move._pdp_get_tax_extract_state() if processed and move.is_sale_document(include_receipts=False) else False
            move.pdp_ppf_lifecycle_state = move._pdp_get_lifecycle_state() if processed else False

    @api.depends('peppol_move_state', 'peppol_message_uuid')
    def _compute_pdp_can_send_response(self):
        for move in self:
            move.pdp_can_send_response = (
                bool(move.peppol_message_uuid)
                and move.peppol_is_sent
                and move.company_id._get_peppol_proxy_type() == 'pdp'
                and move.partner_id._get_pdp_receiver_identification_info()[0] == 'pdp'
            )

    @api.depends('company_id')
    def _compute_pdp_uses_pdp(self):
        for move in self:
            move.pdp_uses_pdp = self.company_id._get_peppol_proxy_type() == 'pdp'

    @api.depends('peppol_is_sent', 'pdp_uses_pdp', 'move_type')
    def _compute_pdp_is_sent(self):
        for move in self:
            move.pdp_is_sent = move.peppol_is_sent and move.pdp_uses_pdp

    def _pdp_get_paid_amount(self):
        self.ensure_one()
        counterpart_move_type = 'out_invoice' if self.move_type == 'out_refund' else 'out_refund'
        reconciled_amls = self._get_reconciled_amls().filtered(lambda l: l.move_id.move_type != counterpart_move_type)
        return self.direction_sign * sum(reconciled_amls.mapped('balance'))

    def _pdp_get_paid_lifecycle_total_amount(self):
        self.ensure_one()
        paid_responses = self.peppol_response_ids.filtered(
            lambda r: r.response_code == 'PD' and r.pdp_flow_number == '2' and r.pdp_ppf_state != 'error'
        )
        payment_infos = [
            payment_info for response in paid_responses for payment_info in (response.pdp_payment_info or [])
            if payment_info.get('type_code') in PAID_CODES and payment_info.get('currency', '').upper() == 'EUR'
        ]
        return sum(float(info.get('amount', '0')) for info in payment_infos)

    def _pdp_get_response_status(self):
        """Return the PDP response status of the message"""
        self.ensure_one()
        # Non-PDP messages do not have a response status
        if not self.peppol_message_uuid:
            return None

        # Take the latest response status if we have any
        response_message = self.peppol_response_ids.filtered(lambda r: r.pdp_flow_number == '2' and r.peppol_state == 'done')
        latest_response = response_message.sorted(
            lambda l: (STATUS_TO_PROCESS_CONDITION_CODE_PDP.get(l.response_code, '0'), l.pdp_issue_date or datetime.min, l.id), reverse=True
        )[:1]
        return latest_response.response_code

    def _pdp_get_tax_extract_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or not self.peppol_is_sent:
            return False
        tax_extract_responses = self.peppol_response_ids.filtered(lambda l: l.pdp_flow_number == '1' and l.peppol_state == 'done')
        if not tax_extract_responses:
            return 'in_progress'
        states = set(tax_extract_responses.mapped('response_code'))
        if {'refused', 'RE'} & states:
            state = 'error'
        elif 'AP' in states:
            state = 'done'
        elif 'AB' in states:
            state = 'sent'
        else:
            state = False
        return state

    def _pdp_get_lifecycle_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or not self.peppol_is_sent:
            return False
        current_status_responses = self.peppol_response_ids.filtered(lambda l: l.pdp_flow_number == '6')
        if not current_status_responses:
            return 'in_progress' if self.is_sale_document(include_receipts=False) else False
        states = set(current_status_responses.mapped('response_code'))
        if {'refused', 'RE'} & states:
            return 'error'
        return 'sent'

    def _l10n_fr_pdp_get_default_notes(self):
        self.ensure_one()
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        # Only add them when using PDP
        if self.company_id._get_peppol_proxy_type() != 'pdp':
            return {}
        payment_term = self.invoice_payment_term_id
        return {
            'PMT': self.env._("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': html2plaintext(payment_term.note) if payment_term.early_discount else self.env._("No discount for early payment."),
        }

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Extends account_edi_ubl_cii
        customization_id = tree.find('{*}CustomizationID')
        # Note: The CustomizationID alone is not enough because e.g. SuperPDP just sends `urn:cen.eu:en16931:2017`
        #       but still expects the full French validation.
        if customization_id is not None and customization_id.text == PDP_CUSTOMIZATION_ID:
            receiver_endpoint_node = tree.find('./{*}AccountingCustomerParty/{*}Party/{*}EndpointID')
            if receiver_endpoint_node is not None and receiver_endpoint_node.get('schemeID') == '0225':
                return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def action_pdp_open_response_wizard(self, **wizard_kwargs):
        if not (pdp_moves := self.filtered('pdp_can_send_response')):
            raise UserError(self.env._("Cannot send response for any of the journal entries."))
        wizard = self.env['pdp.response.wizard'].create({'move_ids': pdp_moves.ids, **wizard_kwargs})
        return wizard._get_records_action(name=self.env._("Send Response Message"), target='new')

    def _post(self, soft=True):
        res = super()._post(soft)
        for company, moves in self.filtered('pdp_can_send_response').grouped('company_id').items():
            company.account_peppol_edi_user._pdp_send_response(moves, 'AP')
        return res

    def button_cancel(self):
        res = super().button_cancel()
        status = None
        if all(move.is_sale_document(include_receipts=True) for move in self):
            status = 'cancelled'
        if all(move.is_purchase_document(include_receipts=True) for move in self):
            status = 'refused'
        if status and self.filtered('pdp_can_send_response') and (action := self.action_pdp_open_response_wizard(status=status)):
            return action

        for move in self:
            if move.state == 'posted' and move.l10n_fr_pdp_sent_in_flow_ids:
                # move was sent, must rectify
                self.env['l10n.fr.pdp.reports.flow']._get_open_flow_and_create_if_needed(move)
                move.with_context(l10n_fr_pdp_bypass_draft_check=True).button_draft()
        return res

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends(
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'date',
        'l10n_fr_pdp_flow_10_operation_type',
        'l10n_fr_pdp_flow_10_report_type',
        'l10n_fr_pdp_has_error',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'move_type',
    )
    def _compute_l10n_fr_pdp_last_flow_id(self):
        scopes_moves_map = defaultdict(list)
        Flow = self.env['l10n.fr.pdp.reports.flow']
        for move in self:
            if move.l10n_fr_pdp_flow_10_report_type:
                scopes_moves_map[frozendict(Flow._get_scope_params_for_move(move))].append(move.id)
            else:
                move.l10n_fr_pdp_last_flow_id = None
        for scope, move_ids in dict(scopes_moves_map).items():
            moves = self.browse(move_ids)
            domain = [(key, '=', value) for key, value in scope.items()]
            last_flow = Flow.search(
                domain=domain,
                order='id desc',
                limit=1,
            )
            if not last_flow or (last_flow.state in FLOW_SENT_STATES and not move.l10n_fr_pdp_sent_in_flow_ids):
                last_flow = Flow._get_open_flow_and_create_if_needed(moves[0])
            moves.l10n_fr_pdp_last_flow_id = last_flow

    @api.depends(
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'date',
        'l10n_fr_pdp_flow_10_report_type',
        'l10n_fr_pdp_has_error',
        'l10n_fr_pdp_last_flow_id',
        'l10n_fr_pdp_last_flow_id.state',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'move_type',
        'state',
    )
    def _compute_l10n_fr_pdp_status(self):
        today = fields.Date.context_today(self)
        for move in self:
            if move.state == 'draft':
                move.l10n_fr_pdp_status = None
            elif not move.l10n_fr_pdp_flow_10_report_type:
                move.l10n_fr_pdp_status = 'out_of_scope'
            elif move.l10n_fr_pdp_has_error:
                move.l10n_fr_pdp_status = 'error'
            elif not move.l10n_fr_pdp_last_flow_id:
                move.l10n_fr_pdp_status = None
            elif move.l10n_fr_pdp_last_flow_id.period_end >= today:
                move.l10n_fr_pdp_status = 'pending'
            else:
                move.l10n_fr_pdp_status = move.l10n_fr_pdp_last_flow_id.state

    @api.depends(
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'is_move_sent',
        'l10n_fr_pdp_flow_10_report_type',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'move_type',
        'name',
        'state',
    )
    def _compute_l10n_fr_pdp_has_error(self):
        for move in self:
            move.l10n_fr_pdp_has_error = bool(move._get_l10n_fr_pdp_errors(lazy=True))

    @api.depends(
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'company_id.account_peppol_edi_user',
        'company_id.l10n_fr_f10_enable_reporting',
        'company_id.l10n_fr_pdp_send_to_ppf',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'state',
    )
    def _compute_l10n_fr_pdp_flow_10_operation_type(self):
        for move in self:
            if move.state == 'draft' or not move.company_id.l10n_fr_f10_enable_reporting:
                move.l10n_fr_pdp_flow_10_operation_type = None
                continue
            matched = move._l10n_fr_pdp_get_matched_transactions()
            tagret_move = matched[0] if matched else move
            if tagret_move._l10n_fr_pdp_is_purchase():
                move.l10n_fr_pdp_flow_10_operation_type = 'purchase'
            elif tagret_move._l10n_fr_pdp_is_sale():
                move.l10n_fr_pdp_flow_10_operation_type = 'sale'
            else:
                move.l10n_fr_pdp_flow_10_operation_type = None

    @api.depends(
        'date',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'company_id.l10n_fr_f10_enable_reporting',
        'company_id.l10n_fr_pdp_annuaire_start_date',
        'company_id.l10n_fr_pdp_periodicity',
        'l10n_fr_pdp_flow_10_operation_type',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'move_type',
        'state',
    )
    def _compute_l10n_fr_pdp_flow_10_report_type(self):
        for move in self:
            if (
                move.state == 'draft'
                or not move.company_id.l10n_fr_f10_enable_reporting
                or not move.company_id._pdp_get_flow_10_start_date()
                or move.date < move.company_id._pdp_get_flow_10_start_date()
                or not move._l10n_fr_pdp_get_transaction_type()  # is b2bi or b2c
            ):
                move.l10n_fr_pdp_flow_10_report_type = None
                continue
            is_purchase = move._l10n_fr_pdp_is_purchase()
            is_sale = not is_purchase and move._l10n_fr_pdp_is_sale()
            if is_purchase or is_sale:
                move.l10n_fr_pdp_flow_10_report_type = 'transaction'
            elif move.move_type == 'entry':
                if move._l10n_fr_pdp_get_matched_transactions():
                    move.l10n_fr_pdp_flow_10_report_type = 'payment'
                else:
                    if move.l10n_fr_pdp_sent_in_flow_ids:
                        # payment was sent but is not linked to an invoice anymore, must create rectificative flow
                        self.env['l10n.fr.pdp.reports.flow']._get_open_flow_and_create_if_needed(move)
                    move.l10n_fr_pdp_flow_10_report_type = None
            else:
                move.l10n_fr_pdp_flow_10_report_type = None

    @api.depends(
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'company_id.account_fiscal_country_id',
        'date',
        'l10n_fr_pdp_flow_10_report_type',
        'line_ids.matched_credit_ids.credit_move_id',
        'line_ids.matched_debit_ids.debit_move_id',
        'move_type',
    )
    def _compute_l10n_fr_pdp_error_message(self):
        for move in self:
            if move.l10n_fr_pdp_last_flow_id.state == 'error':
                move.l10n_fr_pdp_error_message = self.env._('Last Flow is in error')
                continue
            errors = move._get_l10n_fr_pdp_errors()
            move.l10n_fr_pdp_error_message = '- ' + '\n- '.join(errors) if errors else None

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    def _l10n_fr_pdp_get_matched_transactions(self):
        """If self is a payment move, this method returns the transactions it's paying."""
        self.ensure_one()
        if self.move_type != 'entry':
            return

        return self._get_reconciled_amls().move_id.filtered(
            lambda move: move.l10n_fr_pdp_flow_10_report_type == 'transaction' and (
                move._is_downpayment()
                or any(tax.tax_exigibility == 'on_payment' for tax in move.invoice_line_ids.tax_ids)
            )
        )

    def _l10n_fr_pdp_is_sale(self):
        self.ensure_one()
        return self.is_sale_document(include_receipts=True)

    def _l10n_fr_pdp_is_purchase(self):
        self.ensure_one()
        return self.is_purchase_document(include_receipts=False)  # Purchase receipts are not in Flow10 scope as they do not have VAT to report.

    def _get_l10n_fr_pdp_errors(self, lazy=False):
        """Return the list of validation errors for this move in the context of PDP reporting."""
        self.ensure_one()
        if self.state != 'posted' or self.l10n_fr_pdp_flow_10_report_type == 'payment':  # all the checks concerns transactions properties
            return []

        def check():
            if self.is_sale_document(include_receipts=True) and not self.is_move_sent:
                yield self.env._("Invoice/credit note has not been sent to the customer.")
            if transaction_type == 'b2bi':
                try:
                    self.commercial_partner_id.check_vat()
                except ValidationError:
                    yield self.env._("Invalid partner VAT (%(vat)s).", vat=self.commercial_partner_id.vat)

            for move in (self + self._l10n_fr_pdp_get_referenced_documents()):
                if not move or move.move_type == 'entry':
                    continue
                ref_move = self.env._(" in referenced move %s", move.name) if move != self else ""
                if not move.name or not G1_05_RE.match(move.name):
                    yield self.env._("Move name is not valid%s.", ref_move)
                if not move.partner_shipping_id.street:
                    yield self.env._("Missing address street (line 1)%s.", ref_move)
                if not move.partner_shipping_id.city:
                    yield self.env._("Missing address city%s.", ref_move)
                if not move.partner_shipping_id.zip:
                    yield self.env._("Missing address zip code%s.", ref_move)
                if not move.partner_shipping_id.zip:
                    yield self.env._("Missing address country%s.", ref_move)

        transaction_type = self._l10n_fr_pdp_get_transaction_type()
        if lazy:
            error = next(check(), False)
            return [error] if error else []
        return list(check())

    def _l10n_fr_pdp_get_referenced_documents(self):
        self.ensure_one()
        referenced = self.reversed_entry_id
        if 'debit_origin_id' in self._fields:
            referenced += self.debit_origin_id
        return referenced

    def _l10n_fr_pdp_get_transaction_type(self):
        """Classify invoice for PDP reporting: b2c, b2bi, or False (domestic B2B)."""
        self.ensure_one()

        if matched_moves := self._l10n_fr_pdp_get_matched_transactions():
            # if payment, get matched move transaction type
            move = matched_moves[0]
        else:
            move = self

        company_country_code = move.company_id.account_fiscal_country_id.code
        partner_country_code = move.commercial_partner_id.country_id.code
        partner_vat = move.commercial_partner_id.vat
        operation_type = move.l10n_fr_pdp_flow_10_operation_type

        if not operation_type:
            return None

        # partner has no vat -> b2c, if is sale, else no VAT has to be reported
        if operation_type == 'sale' and (not partner_vat or len(partner_vat) == 1):
            return 'b2c'

        if not partner_country_code:
            partner_country_code = self.env['res.country'].search(
                [('code', '=', move.commercial_partner_id._deduce_country_code())],
                limit=1,
            ).code
            if not partner_country_code:
                return None

        company_territory_type = drom_com_territories.get_territory_type(company_country_code)
        partner_territory_type = drom_com_territories.get_territory_type(partner_country_code)
        # One party outside French territories => International
        if not partner_territory_type or not company_territory_type:
            return 'b2bi'

        # all companies are in e-invoicing zones
        if {company_territory_type, partner_territory_type}.issubset(drom_com_territories.E_INVOICING_ZONES):
            return None  # b2b

        # All other cases: International
        return 'b2bi'

    # -------------------------------------------------------------------------
    # CRUD Override
    # -------------------------------------------------------------------------

    def _check_draftable(self):
        """Prevent resetting to draft when invoice already sent to PDP."""
        if not self.env.context.get('l10n_fr_pdp_bypass_draft_check') and self.l10n_fr_pdp_sent_in_flow_ids:
            raise UserError(self.env._(
                "You cannot reset an invoice to draft if it was already sent to PDP. "
                "Create a credit note and issue a new invoice instead or cancel this invoice."
            ))
        return super()._check_draftable()
