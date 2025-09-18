from odoo import fields, models
from odoo.fields import Command
from odoo.tools.translate import _


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    # ------------------------------------------------------------
    # FIELDS
    # ------------------------------------------------------------

    buy_to_resupply = fields.Boolean(
        string="Buy to Resupply",
        default=True,
        compute="_compute_buy_to_resupply",
        inverse="_inverse_buy_to_resupply",
        help="When products are bought, they can be delivered to this warehouse",
    )
    buy_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Buy rule",
        copy=False,
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    def _compute_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            warehouse.buy_to_resupply = bool(
                buy_route.product_selectable
                or buy_route.warehouse_ids.filtered(lambda w: w.id == warehouse.id),
            )

    # ------------------------------------------------------------
    # INVERSE METHODS
    # ------------------------------------------------------------

    def _inverse_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            if not buy_route:
                buy_route = (
                    self.env["stock.rule"]
                    .search(
                        [("action", "=", "buy"), ("warehouse_id", "=", warehouse.id)],
                    )
                    .route_id
                )
            if warehouse.buy_to_resupply:
                buy_route.warehouse_ids = [Command.link(warehouse.id)]
            else:
                buy_route.warehouse_ids = [Command.unlink(warehouse.id)]

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _create_or_update_route(self):
        purchase_route = self._find_or_create_global_route(
            "purchase_stock.route_warehouse0_buy",
            _("Buy"),
        )
        for warehouse in self:
            if warehouse.buy_to_resupply:
                purchase_route.warehouse_ids = [Command.link(warehouse.id)]
        return super()._create_or_update_route()

    def _generate_global_route_rules_values(self):
        rules = super()._generate_global_route_rules_values()
        location_id = self.lot_stock_id
        rules.update(
            {
                "buy_pull_id": {
                    "depends": ["reception_steps", "buy_to_resupply"],
                    "create_values": {
                        "action": "buy",
                        "picking_type_id": self.in_type_id.id,
                        "company_id": self.company_id.id,
                        "route_id": self._find_or_create_global_route(
                            "purchase_stock.route_warehouse0_buy",
                            _("Buy"),
                        ).id,
                        "propagate_cancel": self.reception_steps != "one_step",
                    },
                    "update_values": {
                        "active": self.buy_to_resupply,
                        "name": self._format_rulename(location_id, False, "Buy"),
                        "location_dest_id": location_id.id,
                        "propagate_cancel": self.reception_steps != "one_step",
                    },
                },
            },
        )
        return rules

    def _get_all_routes(self):
        routes = super()._get_all_routes()
        routes |= (
            self.filtered(
                lambda self: self.buy_to_resupply
                and self.buy_pull_id
                and self.buy_pull_id.route_id,
            )
            .mapped("buy_pull_id")
            .mapped("route_id")
        )
        return routes

    def get_rules_dict(self):
        result = super().get_rules_dict()
        for warehouse in self:
            result[warehouse.id].update(warehouse._get_receive_rules_dict())
        return result

    def _get_routes_values(self):
        routes = super()._get_routes_values()
        routes.update(self._get_receive_routes_values("buy_to_resupply"))
        return routes

    def _update_name_and_code(self, name=False, code=False):
        res = super()._update_name_and_code(name, code)
        warehouse = self[0]
        # change the buy stock rule name
        if warehouse.buy_pull_id and name:
            warehouse.buy_pull_id.write(
                {"name": warehouse.buy_pull_id.name.replace(warehouse.name, name, 1)},
            )
        return res
