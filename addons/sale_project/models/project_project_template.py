from odoo import models, fields


class ProjectProjectTemplate(models.Model):
    _inherit = "project.project.template"

    allow_billable = fields.Boolean("Billable")
