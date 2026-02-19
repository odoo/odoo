from odoo import fields, models


class HrVersion(models.Model):
    _inherit = "hr.version"

    job_title = fields.Char(string="Job Title")
