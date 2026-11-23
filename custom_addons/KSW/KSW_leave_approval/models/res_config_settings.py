from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    x_hr_leave_manager_id = fields.Many2one(
        'res.users',
        related='company_id.x_hr_leave_manager_id',
        readonly=False,
        string='HR Leave Manager',
        help='The person responsible for the final approval of time off requests.'
    )
