from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    project_id = fields.Many2one(
        comodel_name="project.project",
        readonly=True,
    )

    def _get_fields_select(self):
        fields = super()._get_fields_select()
        fields["project_id"] = "o.project_id"
        return fields
