# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    email_sent = fields.Boolean(default=False)
    ip_connected = fields.Boolean(default=False)
    manually_set_present = fields.Boolean(default=False)
    manually_set_presence = fields.Boolean(default=False)
    hr_presence_state_display = fields.Selection([
        ('out_of_working_hour', 'Off-Hours'),
        ('present', 'Present'),
        ('absent', 'Absent'),
        ], default='out_of_working_hour')
