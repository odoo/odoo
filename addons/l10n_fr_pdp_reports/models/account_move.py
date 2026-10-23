import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_fr_pdp_flow_ids = fields.Many2many(
        comodel_name="l10n.fr.pdp.flow",
        relation="l10n_fr_pdp_flow_move_rel",
        column1="move_id",
        column2="flow_id",
        string="PDP Flows",
        readonly=True,
        copy=False,
    )
    l10n_fr_pdp_status = fields.Selection(
        selection=[
            ("not_applicable", "Outside PDP scope"),
            ("missing", "Not scheduled"),
            ("draft", "Draft flow"),
            ("ready", "Ready to send"),
            ("pending", "Pending transport"),
            ("done", "Sent"),
            ("error", "Error"),
        ],
        string="E-Reporting Status",
        compute="_compute_l10n_fr_pdp_status",
        store=True,
        copy=False,
        help="Lifecycle of the invoice within the French PDP reporting process.",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends(
        "state",
        "move_type",
        "l10n_fr_pdp_flow_ids.state",
        "l10n_fr_pdp_flow_ids.error_move_ids",
        "l10n_fr_pdp_flow_ids.slice_ids.invalid_move_ids",
        "is_move_sent",
    )
    def _compute_l10n_fr_pdp_status(self):
        for move in self:
            if move.state != "posted" or not move.is_sale_document(include_receipts=True):
                move.l10n_fr_pdp_status = "not_applicable"
                continue

            flows = move.l10n_fr_pdp_flow_ids
            slice_states = set()
            has_invalid = False
            for slice_rec in flows.mapped("slice_ids"):
                if move in slice_rec.move_ids:
                    slice_states.add(slice_rec.state)
                if move in slice_rec.invalid_move_ids:
                    has_invalid = True
            if move in flows.mapped("error_move_ids"):
                has_invalid = True

            if has_invalid or not move.is_move_sent:
                move.l10n_fr_pdp_status = "error"
            elif not slice_states:
                transaction_type = move._get_l10n_fr_pdp_transaction_type()
                if transaction_type:
                    move.l10n_fr_pdp_status = "error"
                else:
                    move.l10n_fr_pdp_status = "not_applicable"
            elif "pending" in slice_states:
                move.l10n_fr_pdp_status = "pending"
            elif "done" in slice_states:
                move.l10n_fr_pdp_status = "done"
            elif "ready" in slice_states:
                move.l10n_fr_pdp_status = "ready"
            elif slice_states & {"draft", "building", "ready", "error"}:
                move.l10n_fr_pdp_status = "draft"
            else:
                move.l10n_fr_pdp_status = "error"

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    @api.model
    def _get_l10n_fr_pdp_flow_domain(self, company, reporting_date):
        """Return domain for invoices eligible for PDP flow on given date."""
        reporting_date = fields.Date.to_date(reporting_date)
        return [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", self.get_sale_types(include_receipts=True)),
            "|",
            ("invoice_date", "=", reporting_date),
            "&",
            ("invoice_date", "=", False),
            ("date", "=", reporting_date),
        ]

    def _get_l10n_fr_pdp_transaction_type(self):
        """Classify invoice for PDP reporting: b2c, international, or False (domestic B2B)."""
        self.ensure_one()
        partner = self.commercial_partner_id
        company_country = self.company_id.country_id
        partner_country = partner.country_id

        # No VAT = B2C domestic
        if not partner.vat or partner.vat == "/":
            return "b2c"
        # Different country = International B2B
        if partner_country and company_country and partner_country != company_country:
            return "international"
        # Same country with VAT = Domestic B2B (not in Flux 10 scope)
        return False

    # -------------------------------------------------------------------------
    # CRUD Override
    # -------------------------------------------------------------------------

    def write(self, vals):
        """Reset open PDP flows when tracked fields change."""
        tracked_fields = {"invoice_date", "date", "invoice_line_ids", "currency_id", "partner_id", "partner_shipping_id", "move_type", "state", "is_move_sent"}
        prev_states = {move.id: move.state for move in self}
        res = super().write(vals)
        if tracked_fields.intersection(vals.keys()):
            open_states = {"draft", "building", "ready", "error"}
            flows_to_reset = self.env["l10n.fr.pdp.flow"].browse()
            for move in self:
                if move.state != "posted" or not move.is_sale_document(include_receipts=True):
                    continue
                open_flows = move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in open_states)
                if open_flows:
                    flows_to_reset |= open_flows
            if flows_to_reset:
                flows_to_reset._mark_as_outdated()
            # Spawn corrective transaction flow when a sent flow exists and invoice changed.
            self.env["l10n.fr.pdp.flow"]._create_corrections_for_moves(self)
        if "is_move_sent" in vals:
            affected = self.filtered(lambda m: m.state == "posted" and m.is_sale_document(include_receipts=True))
            if affected:
                flows = affected.mapped("l10n_fr_pdp_flow_ids").filtered(lambda f: f.state in {"draft", "building", "ready", "error"})
                if flows:
                    flows._mark_as_outdated()
                    try:
                        flows._build_payload()
                    except Exception:
                        _logger.exception("Failed to rebuild PDP payload after send flag change")
        # Create rectificative flows for cancellations of previously sent invoices.
        if "state" in vals and vals.get("state") == "cancel":
            sent_flows = self.env["l10n.fr.pdp.flow"].browse()
            for move in self:
                if prev_states.get(move.id) != "posted":
                    continue
                if not move.is_sale_document(include_receipts=True):
                    continue
                sent_flows |= move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in {'pending', 'done'})
            for flow in sent_flows:
                flow._create_derived_flow('RE')
        return res
