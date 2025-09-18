from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Warehouse",
        readonly=True,
    )

    def _get_select_fields(self):
        fields = super()._get_select_fields()
        fields["warehouse_id"] = "o.warehouse_id"
        return fields

    def _get_group_by_fields(self):
        fields = super()._get_group_by_fields()
        fields.append("o.warehouse_id")
        return fields
