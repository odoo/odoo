from odoo import fields, models


class HrRecruitmentConfig(models.Model):
    _name = "hr_recruitment.config"
    _description = "A company's hr recruitment configuration"
    _inherit = ["mixin.company.config"]

    job_properties_definition = fields.PropertiesDefinition(string="Job Properties")
