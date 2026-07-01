from odoo import fields, models


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = ["hr.version"]
    date_version = fields.Date(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    employee_type = fields.Selection(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    department_id = fields.Many2one(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    is_custom_job_title = fields.Boolean(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    contract_template_id = fields.Many2one(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    structure_type_id = fields.Many2one(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    wage = fields.Monetary(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
    contract_type_id = fields.Many2one(groups="hr.group_hr_user,hr_recruitment.group_hr_recruitment_user")
