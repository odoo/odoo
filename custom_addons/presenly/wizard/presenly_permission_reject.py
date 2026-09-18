from odoo import fields, models
from odoo.exceptions import UserError


class PresenlyPermissionRejectWizard(models.TransientModel):
    _name = 'presenly.permission.reject.wizard'
    _description = 'Reject Presenly Permission Request'

    permission_id = fields.Many2one('presenly.permission', required=True, readonly=True)
    reason = fields.Text(required=True)

    def action_reject(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError('A rejection reason is required.')
        self.permission_id.action_reject(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}
