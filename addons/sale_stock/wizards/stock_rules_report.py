from odoo import fields, models


class StockRulesReport(models.TransientModel):
    _inherit = "stock.rules.report"

    so_route_ids = fields.Many2many(
        comodel_name="stock.route",
        string="Apply specific routes",
        help="Choose to apply SO lines specific routes.",
        domain="[('sale_selectable', '=', True)]",
    )

    def _prepare_report_data(self):
        data = super()._prepare_report_data()
        data["so_route_ids"] = self.so_route_ids.ids
        return data
