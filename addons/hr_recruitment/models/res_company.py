# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    job_properties_definition = fields.PropertiesDefinition("Job Properties")
    applicant_properties_definition = fields.PropertiesDefinition("Applicant Properties", groups="hr_recruitment.group_hr_recruitment_interviewer")
