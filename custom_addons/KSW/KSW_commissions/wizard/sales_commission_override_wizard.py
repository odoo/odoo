"""Wizard: Sales-manager override reason capture.

Opened by ``ksw.sales.commission.line.action_open_override_wizard``.
The manager enters the justification, clicks Apply, and the wizard
calls back into the line to stamp the override fields and chatter
the sheet.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KswSalesCommissionOverrideWizard(models.TransientModel):
    _name = 'ksw.sales.commission.override.wizard'
    _description = 'Sales-Manager Commission Condition Override Wizard'

    line_id = fields.Many2one(
        'ksw.sales.commission.line', required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        related='line_id.employee_id', readonly=True,
    )
    role = fields.Selection(
        related='line_id.role', readonly=True,
    )
    sales_pct = fields.Float(
        related='line_id.sales_pct', readonly=True,
    )
    collection_pct = fields.Float(
        related='line_id.collection_pct', readonly=True,
    )
    commission_kind = fields.Char(
        compute='_compute_commission_kind', string='Commission Type',
    )
    reason = fields.Char(
        required=True,
        help='Brief justification for granting the commission despite '
             'the unmet condition. Stored on the line and posted to '
             'the sheet chatter for audit.',
    )

    @api.depends(
        'line_id.role',
        'line_id.sales_rule_id',
        'line_id.collection_rule_id',
        'line_id.combined_rule_id',
    )
    def _compute_commission_kind(self):
        """Determine commission label based on which rule / tier ladder is
        actually active for this line.

        Logic (in order):
          - If only a collection rule is resolved  → "Coll. Comm."
          - If only a sales rule is resolved        → "Sales Comm."
          - If a combined rule is resolved          → "Combined Comm."
          - role='both' without combined rule       → "Sales & Coll. Comm."
          - Fallback by role name otherwise.
        """
        for rec in self:
            line = rec.line_id
            has_sales = bool(line.sales_rule_id)
            has_coll = bool(line.collection_rule_id)
            has_comb = bool(line.combined_rule_id)

            if has_comb:
                rec.commission_kind = _("Combined Comm.")
            elif has_coll and not has_sales:
                rec.commission_kind = _("Coll. Comm.")
            elif has_sales and not has_coll:
                rec.commission_kind = _("Sales Comm.")
            elif has_sales and has_coll:
                rec.commission_kind = _("Sales & Coll. Comm.")
            else:
                # Fall back to role label when no rule is resolved yet.
                role = line.role or 'sales'
                rec.commission_kind = {
                    'sales':    _("Sales Comm."),
                    'collect':  _("Coll. Comm."),
                    'both':     _("Sales & Coll. Comm."),
                }.get(role, _("Commission"))

    def action_apply(self):
        self.ensure_one()
        if not (self.reason or '').strip():
            raise UserError(_("A reason is required to override the "
                              "commission condition."))
        self.line_id._apply_override(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}

