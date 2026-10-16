from odoo import fields, models
from odoo.exceptions import UserError


class PresenlyOvertimeRejectWizard(models.TransientModel):
    _name = 'presenly.overtime.reject.wizard'
    _description = 'Reject Presenly Overtime Request'

    overtime_id = fields.Many2one(
        'presenly.overtime.request', required=True, readonly=True,
    )
    reason = fields.Text(required=True)

    def action_reject(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError('A rejection reason is required.')
        self.overtime_id.action_presenly_reject(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}