from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_annual_leave = fields.Boolean(
        string='Is Annual Leave',
        default=False,
        help='Check this box if this leave type represents annual leave.',
    )

    leave_validation_type = fields.Selection(
        selection_add=[
            ('annual_multi', 'Annual Leave – Multi-Step Approval'),
        ],
        ondelete={'annual_multi': 'set default'},
    )
