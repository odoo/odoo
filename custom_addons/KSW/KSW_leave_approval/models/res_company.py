from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    x_hr_leave_manager_id = fields.Many2one(
        'res.users',
        string='HR Leave Manager',
        help='The person responsible for the final approval of time off requests.'
    )
