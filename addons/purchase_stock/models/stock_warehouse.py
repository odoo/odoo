from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools.translate import _


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    buy_to_resupply = fields.Boolean(
        string="Buy to Resupply",
        compute="_compute_buy_to_resupply",
        inverse="_inverse_buy_to_resupply",
        default=True,
        help="When products are bought, they can be delivered to this warehouse",
    )
    buy_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Buy rule",
        copy=False,
    )

    @api.depends("buy_pull_id.route_id.warehouse_ids")
    def _compute_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            warehouse.buy_to_resupply = warehouse in buy_route.warehouse_ids

    def _inverse_buy_to_resupply(self):
        for warehouse in self:
            buy_route = warehouse.buy_pull_id.route_id
            if not buy_route:
                buy_route = self.env["stock.rule"]._get_buy_routes(warehouse=warehouse)
            if warehouse.buy_to_resupply:
                buy_route.warehouse_ids = [Command.link(warehouse.id)]
            else:
                buy_route.warehouse_ids = [Command.unlink(warehouse.id)]

    def _create_or_update_route(self):
        purchase_route = self._get_or_create_global_route(
            "purchase_stock.route_warehouse0_buy",
            _("Buy"),
        )
        to_link = self.filtered("buy_to_resupply")
        if to_link:
            purchase_route.warehouse_ids = [Command.link(wh.id) for wh in to_link]
        return super()._create_or_update_route()

    def _prepare_global_route_rule_vals(self):
        rules = super()._prepare_global_route_rule_vals()
        location_id = self.lot_stock_id
        rules.update(
            {
                "buy_pull_id": {
                    "depends": ["reception_steps", "buy_to_resupply"],
                    "create_values": {
                        "action": "buy",
                        "picking_type_id": self.in_type_id.id,
                        "company_id": self.company_id.id,
                        "route_id": self._get_or_create_global_route(
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

    def _get_fields_route_trigger(self):
        return super()._get_fields_route_trigger() | {"buy_to_resupply"}

    def _get_global_rule_fields(self):
        return super()._get_global_rule_fields() | {"buy_pull_id"}

    def _get_all_routes(self):
        routes = super()._get_all_routes()
        routes |= self.filtered(
            lambda warehouse: (
                warehouse.buy_to_resupply and warehouse.buy_pull_id.route_id
            ),
        ).buy_pull_id.route_id
        return routes

    def _prepare_rule_routings(self):
        result = super()._prepare_rule_routings()
        for warehouse in self:
            result[warehouse.id].update(
                warehouse._prepare_internal_reception_routings()
            )
        return result

    def _prepare_route_vals(self):
        routes = super()._prepare_route_vals()
        routes.update(self._prepare_receive_route_vals("buy_to_resupply"))
        return routes
