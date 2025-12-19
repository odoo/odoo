from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from odoo.addons.l10n_fr_pdp.models.account_edi_proxy_user import STATUS_TO_PROCESS_CONDITION_CODE_PDP
from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID
from odoo.addons.l10n_fr_pdp.models.account_peppol_response import NEW_STATUSES

PAID_CODES = frozenset({'ESC', 'RAB', 'REM', 'MPA', 'MEN'})


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

    @api.depends('peppol_is_sent')
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account' to hide the reset to draft button for sent PDP invoices
        super()._compute_show_reset_to_draft_button()
        relevant_moves = self.filtered(lambda move: move.pdp_is_sent and move.is_sale_document(include_receipts=True))
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
            move.pdp_uses_pdp = move.company_id._get_peppol_proxy_type() == 'pdp'

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
        return res
