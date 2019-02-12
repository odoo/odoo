# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_org_chart = fields.Boolean(string="Show Organizational Chart")
    module_hr_presence = fields.Boolean(string="Control presence of employees")
    hr_presence_control_login = fields.Boolean(string="According to the system login (User status on chat)", config_parameter='hr.hr_presence_control_login')
    hr_presence_control_email = fields.Boolean(string="According to the amount of sent emails", config_parameter='hr.hr_presence_control_email')
    hr_presence_control_ip = fields.Boolean(string="According to the IP address", config_parameter='hr.hr_presence_control_ip')
    hr_employee_self_edit = fields.Boolean(string="Employee Edition", config_parameter='hr.hr_employee_self_edit')
