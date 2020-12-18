# -*- coding: utf-8 -*-

import threading
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_presence = fields.Boolean(string="Advanced Presence Control")
    module_hr_skills = fields.Boolean(string="Skills Management")
    hr_presence_control_login = fields.Boolean(string="Based on user status in system", config_parameter='hr.hr_presence_control_login')
    hr_presence_control_email = fields.Boolean(string="Based on number of emails sent", config_parameter='hr_presence.hr_presence_control_email')
    hr_presence_control_ip = fields.Boolean(string="Based on IP Address", config_parameter='hr_presence.hr_presence_control_ip')
    module_hr_attendance = fields.Boolean(string="Based on attendances")
    hr_presence_control_email_amount = fields.Integer(related="company_id.hr_presence_control_email_amount", readonly=False)
    hr_presence_control_ip_list = fields.Char(related="company_id.hr_presence_control_ip_list", readonly=False)
    hr_employee_self_edit = fields.Boolean(string="Employee Editing", config_parameter='hr.hr_employee_self_edit')

    @api.constrains('module_hr_presence', 'hr_presence_control_email', 'hr_presence_control_ip')
    def _check_advanced_presence(self):
        test_mode = self.env.registry.in_test_mode() or getattr(threading.currentThread(), 'testing', False)
        if self.env.context.get('install_mode', False) or test_mode:
            return

        for settings in self:
            if settings.module_hr_presence and not (settings.hr_presence_control_email or settings.hr_presence_control_ip):
                raise ValidationError(_('You should select at least one Advanced Presence Control option.'))
