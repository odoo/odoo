from odoo import fields, models
from odoo.exceptions import UserError


class PresenlyLeaveRejectWizard(models.TransientModel):
    _name = 'presenly.leave.reject.wizard'
    _description = 'Reject Presenly Leave Request'

    leave_id = fields.Many2one('hr.leave', required=True, readonly=True)
    reason = fields.Text(required=True)

    def action_reject(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError('A rejection reason is required.')
        self.leave_id.action_presenly_reject(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}
