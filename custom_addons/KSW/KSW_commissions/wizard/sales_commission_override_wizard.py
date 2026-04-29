"""Wizard: Sales-manager override reason capture.

Opened by ``ksw.sales.commission.line.action_open_override_wizard``.
The manager enters the justification, clicks Apply, and the wizard
calls back into the line to stamp the override fields and chatter
the sheet.
"""
from odoo import _, fields, models
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
    sales_pct = fields.Float(
        related='line_id.sales_pct', readonly=True,
    )
    collection_pct = fields.Float(
        related='line_id.collection_pct', readonly=True,
    )
    reason = fields.Char(
        required=True,
        help='Brief justification for granting the commission despite '
             'the unmet condition. Stored on the line and posted to '
             'the sheet chatter for audit.',
    )

    def action_apply(self):
        self.ensure_one()
        if not (self.reason or '').strip():
            raise UserError(_("A reason is required to override the "
                              "commission condition."))
        self.line_id._apply_override(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}

