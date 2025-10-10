from odoo import models, fields


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    job_title = fields.Char(related='employee_id.job_title', string="Job Title")
