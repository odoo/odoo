from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_annual_leave = fields.Boolean(
        string='Is Annual Leave',
        default=False,
        help='Check this box if this leave type represents annual leave.',
    )

