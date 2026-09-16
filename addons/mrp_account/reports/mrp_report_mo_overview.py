from odoo import models


class ReportMrpReport_Mo_Overview(models.AbstractModel):
    _inherit = "report.mrp.report_mo_overview"

    def _get_unit_cost(self, move):
        if move.state == "done":
            price_unit = move._get_price_unit()
            return move.product_id.uom_id._get_price_in_unit(
                price_unit, move.product_uom_id
            )
        return super()._get_unit_cost(move)
