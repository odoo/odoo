from odoo import api, fields, models


class MixinStockReplenish(models.AbstractModel):
    _inherit = "mixin.stock.replenish"

    supplier_id = fields.Many2one(
        comodel_name="product.supplierinfo",
        string="Vendor",
    )
    show_vendor = fields.Boolean(compute="_compute_show_vendor")

    @api.depends("route_id")
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec._is_vendor_shown(rec.route_id)

    def _is_vendor_shown(self, route):
        return route._has_buy_rule()
