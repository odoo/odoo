from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    is_subcontract = fields.Boolean(
        search="_search_is_subcontract",
        store=False,
    )

    def _search_is_subcontract(self, operator, value):
        if operator != "in":
            return NotImplemented
        subcontracting_location_ids = self.env.companies.subcontracting_location_id.child_internal_location_ids.ids
        return [("location_id", operator, subcontracting_location_ids)]
