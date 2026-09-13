from odoo import fields, models


class ProjectWorkflowStep(models.Model):
    _inherit = "project.workflow.step"

    sms_template_id = fields.Many2one(
        comodel_name="sms.template",
        string="SMS Template",
        domain=[("model", "=", "project.task")],
        help="If set, an SMS Text Message will be automatically sent to the customer when the task reaches this stage.",
    )
