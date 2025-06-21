from odoo import fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    partner_id = fields.Many2one("res.partner")
    allow_billable = fields.Boolean(related="template_id.allow_billable")

    def _get_template_whitelist_fields(self):
        res = super()._get_template_whitelist_fields()
        if self.allow_billable:
            res.append("partner_id")
        return res
