# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Company Working Hours',
        related='company_id.resource_calendar_id', readonly=False)
    module_hr_org_chart = fields.Boolean(string="Organizational Chart")
    module_hr_presence = fields.Boolean(string="Presence Control")
    module_hr_skills = fields.Boolean(string="Skills Management")
    hr_employee_self_edit = fields.Boolean(string="Allow Updating Personal Data", config_parameter='hr.hr_employee_self_edit')
