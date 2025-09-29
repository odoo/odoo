from odoo import models, fields


class HrVersion(models.Model):
    _inherit = "hr.version"

    job_title = fields.Char(compute="_compute_job_title", inverse="_inverse_job_title", store=True, readonly=False,
        string="Job Title", tracking=True)
