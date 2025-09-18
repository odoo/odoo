from odoo import api, fields, models


class StockReplenishMixin(models.AbstractModel):
    _inherit = "stock.replenish.mixin"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    supplier_id = fields.Many2one(
        comodel_name="product.supplierinfo",
        string="Vendor",
    )
    show_vendor = fields.Boolean(
        compute="_compute_show_vendor",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("route_id")
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec._get_show_vendor(rec.route_id)

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_show_vendor(self, route):
        return any(r.action == "buy" for r in route.rule_ids)
