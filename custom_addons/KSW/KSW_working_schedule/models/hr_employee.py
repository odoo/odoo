from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    main_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Main Work Schedule',
        domain="[('is_temp_schedule', '=', False)]",
        help='The main work schedule for the employee, used for attendance analysis',
    )

    temp_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Temporary Work Schedule',
        domain="[('is_temp_schedule', '=', True)]",
        help='The temporary work schedule for the employee, used for attendance analysis',
    )


