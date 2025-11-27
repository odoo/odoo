import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.l10n_fr_pdp_reports.utils import drom_com_territories

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_fr_pdp_flow_ids = fields.Many2many(
        comodel_name='l10n.fr.pdp.flow',
        relation='l10n_fr_pdp_flow_move_rel',
        column1='move_id',
        column2='flow_id',
        string="PDP Flows",
        readonly=True,
        copy=False,
    )
    l10n_fr_pdp_status = fields.Selection(
        selection=[
            ('out_of_scope', "Out of scope"),
            ('pending', "Pending"),
            ('ready', "Ready to send"),
            ('error', "Error"),
            ('sent', "Sent"),
            ('cancelled', "Cancelled"),
        ],
        string="E-Reporting Status",
        compute='_compute_l10n_fr_pdp_status',
        store=True,
        copy=False,
        help="Lifecycle of the invoice within the French PDP reporting process.",
    )
    l10n_fr_pdp_invoice_reference = fields.Char(
        string="PDP Invoice Reference Override",
        help="Override the invoice identifier used in Flux 10 payloads (test datasets or specific mappings).",
    )
    l10n_fr_pdp_bt3_code = fields.Char(
        string="PDP BT-3 Invoice Type Code",
        help="Invoice type code (BT-3) used to map TT-21 in Flux 10.1.",
    )
    l10n_fr_pdp_bt8_code = fields.Char(
        string="PDP BT-8 Tax Due Date Type",
        help="Tax due date type code (BT-8) used to map TT-24 in Flux 10.1.",
    )
    l10n_fr_pdp_contract_reference = fields.Char(
        string="PDP Contract Reference (BT-12)",
        help="Contract reference used for TT-30 when BT-3=262.",
    )
    l10n_fr_pdp_billing_period_start = fields.Date(
        string="PDP Billing Period Start (BT-73)",
        help="Billing period start date used for TT-31 when BT-3=262.",
    )
    l10n_fr_pdp_note_blu = fields.Text(
        string="PDP Note BLU",
        help="BLU note content for Flux 10.1 (TT-26/TT-27).",
    )
    l10n_fr_pdp_note_txd = fields.Text(
        string="PDP Note TXD",
        help="TXD note content for Flux 10.1 (TT-26/TT-27).",
    )
    l10n_fr_pdp_note_pai = fields.Text(
        string="PDP Note PAI",
        help="PAI note content for Flux 10.1 (TT-26/TT-27).",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends(
        'state',
        'move_type',
        'partner_id',
        'partner_id.vat',
        'partner_id.country_id',
        'company_id',
        'company_id.country_id',
        'company_id.partner_id.vat',
        'l10n_fr_pdp_flow_ids.state',
        'l10n_fr_pdp_flow_ids.error_move_ids',
        'l10n_fr_pdp_flow_ids.period_status',
        'is_move_sent',
    )
    def _compute_l10n_fr_pdp_status(self):
        for move in self:
            is_sale = move.is_sale_document(include_receipts=True)
            is_purchase = move.is_purchase_document(include_receipts=False)

            # Not posted or not a supported document -> not applicable
            if move.state != 'posted' or not (is_sale or is_purchase):
                move.l10n_fr_pdp_status = False
                continue

            # Check if move is out of scope.
            in_scope = (
                bool(move._get_l10n_fr_pdp_transaction_type())
                if is_sale
                else self._is_international_partner_for_purchase(move)
            )
            if not in_scope:
                move.l10n_fr_pdp_status = 'out_of_scope'
                continue

            # Check if move is in any flow
            flows = move.l10n_fr_pdp_flow_ids
            if not flows:
                # In-scope posted document not aggregated yet.
                move.l10n_fr_pdp_status = 'pending'
                continue

            # Get the most relevant flow for this move (prioritize non-sent flows),
            # then pick the most recent one to avoid stale status from older flows.
            active_flows = flows.filtered(lambda f: f.state not in {'sent', 'completed'})
            relevant_flow = active_flows.sorted('id', reverse=True)[:1] if active_flows else flows.sorted('id', reverse=True)[:1]

            if not relevant_flow:
                move.l10n_fr_pdp_status = False
                continue

            # Check if move has validation errors in the relevant flow
            has_errors = move in relevant_flow.error_move_ids

            # v1.2 Status logic based on period_status:
            # - open period -> pending (users have time to fix errors)
            # - grace period -> error (if validation errors) OR ready (if valid)
            # - closed period -> sent (if flow sent) OR error (will be in auto-created RE)

            # Recompute directly to avoid stale cached value when "today" changes
            # (especially in cron/time-window transitions and tests patching today).
            period_status = relevant_flow._get_period_status()
            flow_state = relevant_flow.state

            # Priority 1: Flow already sent/completed
            if flow_state in {'sent', 'completed'}:
                if has_errors and relevant_flow.transport_status == 'PARTIAL_REJECTED':
                    move.l10n_fr_pdp_status = 'error'
                else:
                    move.l10n_fr_pdp_status = 'sent'
            elif flow_state == 'cancelled':
                move.l10n_fr_pdp_status = 'cancelled'
            # Open period: users have time to fix errors, stay pending.
            elif period_status == 'open':
                move.l10n_fr_pdp_status = 'pending'
            # Grace/closed: validation errors are surfaced.
            elif has_errors:
                move.l10n_fr_pdp_status = 'error'
            # Flow built and valid: ready to send (even on due day / after if not sent yet).
            elif flow_state == 'ready':
                move.l10n_fr_pdp_status = 'ready'
            else:
                move.l10n_fr_pdp_status = 'pending'

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    @api.model
    def _get_l10n_fr_pdp_flow_domain(self, company, reporting_date):
        """Return domain for invoices eligible for PDP flow on given date."""
        reporting_date = fields.Date.to_date(reporting_date)
        return [
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('move_type', 'in', self.get_sale_types(include_receipts=True)),
            '|',
            ('invoice_date', '=', reporting_date),
            '&',
            ('invoice_date', '=', False),
            ('date', '=', reporting_date),
        ]

    def _get_l10n_fr_pdp_transaction_type(self):
        """Classify invoice for PDP reporting: b2c, international, or False (domestic B2B)."""
        self.ensure_one()
        partner = self.commercial_partner_id
        company_country_code = self.company_id.country_id.code if self.company_id.country_id else None
        partner_country_code = partner.country_id.code if partner.country_id else None

        # Use the centralized DROM-COM logic
        return drom_com_territories.get_transaction_flow_type(
            company_country=company_country_code,
            partner_country=partner_country_code,
            partner_vat=partner.vat
        )

    def _is_international_partner_for_purchase(self, move=None):
        """Return True when a vendor bill partner is treated as international for Flux 10."""
        target_move = move or self
        target_move.ensure_one()
        partner = target_move.commercial_partner_id
        company_country_code = target_move.company_id.country_id.code if target_move.company_id.country_id else None
        partner_country_code = partner.country_id.code if partner.country_id else None

        # Purchases are classified on geography/territory rules, not on supplier VAT presence.
        # Missing VAT must stay in-scope and be handled by validation errors.
        if company_country_code and partner_country_code:
            if drom_com_territories.should_use_einvoicing(company_country_code, partner_country_code):
                return False
            company_is_fr = drom_com_territories.is_france_territory(company_country_code)
            partner_is_fr = drom_com_territories.is_france_territory(partner_country_code)
            return not (company_is_fr and partner_is_fr and company_country_code == partner_country_code)

        vat = (partner.vat or '').strip()
        company_country = target_move.company_id.country_id
        if vat and company_country and len(vat) >= 2:
            return vat[:2].upper() != (company_country.code or '')
        return False

    # -------------------------------------------------------------------------
    # CRUD Override
    # -------------------------------------------------------------------------

    def write(self, vals):
        """Reset open PDP flows when tracked fields change."""
        prev_states = {move.id: move.state for move in self}
        tracked_fields = {
            'invoice_date',
            'date',
            'invoice_line_ids',
            'currency_id',
            'partner_id',
            'partner_shipping_id',
            'move_type',
            'state',
            'is_move_sent',
            'l10n_fr_pdp_invoice_reference',
            'l10n_fr_pdp_bt3_code',
            'l10n_fr_pdp_bt8_code',
            'l10n_fr_pdp_contract_reference',
            'l10n_fr_pdp_billing_period_start',
            'l10n_fr_pdp_note_blu',
            'l10n_fr_pdp_note_txd',
            'l10n_fr_pdp_note_pai',
        }
        res = super().write(vals)
        if tracked_fields.intersection(vals):
            open_states = {'draft', 'building', 'ready', 'error'}
            flows_to_reset = self.env['l10n.fr.pdp.flow'].browse()
            for move in self:
                if move.state != 'posted':
                    continue
                if move.is_sale_document(include_receipts=True):
                    if not move._get_l10n_fr_pdp_transaction_type():
                        continue
                elif move.is_purchase_document(include_receipts=False):
                    if not self._is_international_partner_for_purchase(move):
                        continue
                else:
                    continue
                open_flows = move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in open_states)
                if open_flows:
                    flows_to_reset |= open_flows
            if flows_to_reset:
                flows_to_reset._mark_as_outdated()
            # v1.2: No automatic correction flows. User must create credit note + RE manually.
        if 'is_move_sent' in vals:
            affected = self.filtered(lambda m: m.state == 'posted' and m.is_sale_document(include_receipts=True))
            if affected:
                flows = affected.mapped('l10n_fr_pdp_flow_ids').filtered(lambda f: f.state in {'draft', 'building', 'ready', 'error'})
                if flows:
                    flows._mark_as_outdated()
                    try:
                        flows._build_payload()
                    except Exception:
                        _logger.exception('Failed to rebuild PDP payload after send flag change')
        # Create rectificative flows for cancellations of previously sent invoices.
        if 'state' in vals and vals.get('state') == 'cancel':
            sent_flows = self.env['l10n.fr.pdp.flow'].browse()
            for move in self:
                if prev_states.get(move.id) != 'posted':
                    continue
                if not move.is_sale_document(include_receipts=True):
                    continue
                sent_flows |= move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in {'sent', 'completed'})
            for flow in sent_flows:
                flow.action_create_rectificative_flow()
        return res

    def button_draft(self):
        """Prevent resetting to draft when invoice already sent to PDP."""
        for move in self:
            if not move.is_sale_document(include_receipts=True):
                continue
            if move.l10n_fr_pdp_status == 'sent':
                raise UserError(_("You cannot reset to draft an invoice already sent to PDP. Create a credit note and issue a new invoice instead."))
        return super().button_draft()
