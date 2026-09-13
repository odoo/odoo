from odoo import api, fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg


class MixinStockReplenish(models.AbstractModel):
    _name = "mixin.stock.replenish"
    _description = "Product Replenish Mixin"

    route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Preferred Route",
        check_company=True,
        help="Apply specific route for the replenishment instead of product's default routes.",
    )
    allowed_route_ids = fields.Many2many(
        comodel_name="stock.route",
        compute="_compute_allowed_route_ids",
    )

    @api.depends("product_id", "product_tmpl_id")
    def _compute_allowed_route_ids(self):
        domain = self._get_domain_allowed_route()
        route_ids = self.env["stock.route"].search(domain)
        dbg.logic.debug(
            "_compute_allowed_route_ids on %s: %s", dbg.rec(self), dbg.rec(route_ids)
        )
        self.allowed_route_ids = route_ids

    def _get_domain_allowed_route(self):
        inter_company_location = self.env.ref(
            "stock.stock_location_inter_company", raise_if_not_found=False
        )

        base_domain = Domain("product_selectable", "=", True)
        if self.warehouse_id:
            wh_route_ids = self.warehouse_id.route_ids.filtered(
                lambda r: r._is_valid_resupply_route_for_product(self.product_id)
            ).ids
            if wh_route_ids:
                base_domain |= Domain("id", "in", wh_route_ids)

        domains = [
            base_domain,
            Domain("rule_ids.location_dest_id.warehouse_id", "!=", False),
        ]
        if inter_company_location:
            domains += [
                Domain(
                    "rule_ids",
                    "not any",
                    [("location_src_id", "=", inter_company_location.id)],
                ),
                Domain(
                    "rule_ids",
                    "not any",
                    [("location_dest_id", "=", inter_company_location.id)],
                ),
            ]
        return Domain.AND(domains)
