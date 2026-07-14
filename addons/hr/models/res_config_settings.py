
import threading
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_presence = fields.Boolean(string="Advanced Presence Control")
    module_hr_skills = fields.Boolean(string="Skills Management")
    module_hr_homeworking = fields.Boolean(string="Remote Work")
    hr_presence_control_login = fields.Boolean(related='company_id.hr_presence_control_login', readonly=False)
    hr_presence_control_email = fields.Boolean(related='company_id.hr_presence_control_email', readonly=False)
    hr_presence_control_ip = fields.Boolean(related='company_id.hr_presence_control_ip', readonly=False)
    module_hr_attendance = fields.Boolean(related='company_id.hr_presence_control_attendance', readonly=False)
    hr_presence_control_email_amount = fields.Integer(related="company_id.hr_presence_control_email_amount", readonly=False)
    hr_presence_control_ip_list = fields.Char(related="company_id.hr_presence_control_ip_list", readonly=False)
    hr_employee_self_edit = fields.Boolean(string="Employee Editing", config_parameter='hr.hr_employee_self_edit')

    @api.constrains('module_hr_presence', 'hr_presence_control_email', 'hr_presence_control_ip')
    def _check_advanced_presence(self):
        test_mode = self.env.registry.in_test_mode() or getattr(threading.current_thread(), 'testing', False)
        if self.env.context.get('install_mode', False) or test_mode:
            return
