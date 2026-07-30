from odoo import fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_unpaid_leave = fields.Boolean(
        string='Is Unpaid Leave',
        default=False,
        help='Check this box if this leave type represents unpaid leave.',
    )

    leave_validation_type = fields.Selection(
        selection_add=[
            ('unpaid_multi', 'Unpaid Leave – Multi-Step Approval'),
        ],
        ondelete={'unpaid_multi': 'set default'},
    )

