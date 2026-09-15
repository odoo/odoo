from odoo import _, api, fields, models


class CustomPayrollRejectWizard(models.TransientModel):
    _name = 'custom.payroll.reject.wizard'
    _description = 'Reject Payroll Batch Wizard'

    batch_id = fields.Many2one(
        'custom.payroll.batch',
        string='Payroll Batch',
        required=True,
    )
    reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Provide a reason for rejecting this batch. The batch will be reset to Draft.',
    )

    def action_confirm_reject(self):
        self.ensure_one()
        self.batch_id.action_reject(self.reason)
        return {'type': 'ir.actions.act_window_close'}
