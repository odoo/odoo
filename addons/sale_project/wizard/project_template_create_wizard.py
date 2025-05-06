from odoo import fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    allow_billable = fields.Boolean(related="template_id.allow_billable")
