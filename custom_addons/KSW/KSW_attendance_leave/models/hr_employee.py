from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_check_in_only = fields.Boolean(
        string='Check-in Only',
        default=False,
        groups='hr.group_hr_user',
        help='If enabled, only a check-in punch is required. '
             'Early-leave deductions are suppressed; the scheduled end '
             'is used as the effective checkout for worked-hours calculation.',
    )
