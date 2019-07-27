# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_org_chart = fields.Boolean(string="Organizational Chart")
    module_hr_presence = fields.Boolean(string="Advanced Employees Presence Check Based on")
    module_hr_skills = fields.Boolean(string="Employee Skills and Resumé")
    hr_presence_control_login = fields.Boolean(string="The system login (User status on chat)", config_parameter='hr.hr_presence_control_login')
    hr_presence_control_email = fields.Boolean(string="The amount of sent emails", config_parameter='hr_presence.hr_presence_control_email')
    hr_presence_control_ip = fields.Boolean(string="The IP address", config_parameter='hr_presence.hr_presence_control_ip')
    module_hr_attendance = fields.Boolean(string="The Attendance module.")
    hr_presence_control_email_amount = fields.Integer(related="company_id.hr_presence_control_email_amount", readonly=False)
    hr_presence_control_ip_list = fields.Char(related="company_id.hr_presence_control_ip_list", readonly=False)
    hr_employee_self_edit = fields.Boolean(string="Employee Edition", config_parameter='hr.hr_employee_self_edit')
