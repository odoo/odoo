from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_presence = fields.Boolean(string="Advanced Presence Control")
    module_hr_skills = fields.Boolean(string="Skills Management")
    module_hr_contract = fields.Boolean(string="Contracts Management")
    hr_presence_control_login = fields.Boolean(related='company_id.hr_presence_control_login', readonly=False)
    hr_presence_control_email = fields.Boolean(related='company_id.hr_presence_control_email', readonly=False)
    hr_presence_control_ip = fields.Boolean(related='company_id.hr_presence_control_ip', readonly=False)
    module_hr_attendance = fields.Boolean(related='company_id.hr_presence_control_attendance', readonly=False)
    hr_presence_control_email_amount = fields.Integer(related="company_id.hr_presence_control_email_amount", readonly=False)
    hr_presence_control_ip_list = fields.Char(related="company_id.hr_presence_control_ip_list", readonly=False)
    hr_employee_self_edit = fields.Boolean(string="Employee Editing", config_parameter='hr.hr_employee_self_edit')
