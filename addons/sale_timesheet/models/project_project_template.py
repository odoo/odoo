
from odoo import models, fields, api


class ProjectProjectTemplate(models.Model):
    _inherit = "project.project.template"

    allow_billable = fields.Boolean("Billable")
    billing_type = fields.Selection(
        compute="_compute_billing_type",
        selection=[
            ('not_billable', 'not billable'),
            ('manually', 'billed manually'),
        ],
        default='not_billable',
        required=True,
        readonly=False,
        store=True,
    )

    @api.depends('allow_billable', 'allow_timesheets')
    def _compute_billing_type(self):
        self.filtered(lambda project: (not project.allow_billable or not project.allow_timesheets) and project.billing_type == 'manually').billing_type = 'not_billable'
