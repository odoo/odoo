from odoo import fields, models


class ProjectPhase(models.Model):
    _inherit = "project.phase"

    sms_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        domain=[("model", "=", "project.project")],
        help="If set, an SMS Text Message will be automatically sent to the customer when the project reaches this stage.",
    )
