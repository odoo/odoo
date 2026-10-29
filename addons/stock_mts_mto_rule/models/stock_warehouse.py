# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    mto_mts_management = fields.Boolean(
        "Use MTO+MTS rules",
        help="If this new route is selected on product form view, a "
        "purchase order will be created only if the virtual stock is "
        "less than 0 else, the product will be taken from stocks",
    )
    mts_mto_rule_id = fields.Many2one("stock.rule", "MTO+MTS rule", check_company=True)

    def _get_all_routes(self):
        routes = super(StockWarehouse, self)._get_all_routes()
        routes |= self.mapped("mts_mto_rule_id.route_id")
        return routes

    def _update_name_and_code(self, new_name=False, new_code=False):
        res = super(StockWarehouse, self)._update_name_and_code(new_name, new_code)
        if not new_name:
            return res
        for warehouse in self.filtered("mts_mto_rule_id"):
            warehouse.mts_mto_rule_id.write(
                {
                    "name": warehouse.mts_mto_rule_id.name.replace(
                        warehouse.name, new_name, 1
                    ),
                }
            )
        return res

    def _get_route_name(self, route_type):
        if route_type == "mts_mto":
            return _("MTS+MTO")
        return super(StockWarehouse, self)._get_route_name(route_type)

    def _get_global_route_rules_values(self):
        rule = self.get_rules_dict()[self.id][self.delivery_steps]
        rule = [r for r in rule if r.from_loc == self.lot_stock_id][0]
        location_id = rule.from_loc
        location_dest_id = rule.dest_loc
        picking_type_id = rule.picking_type
        res = super(StockWarehouse, self)._get_global_route_rules_values()
        res.update(
            {
                "mts_mto_rule_id": {
                    "depends": ["delivery_steps", "mto_mts_management"],
                    "create_values": {
                        "action": "pull",
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "auto": "manual",
                        "propagate_cancel": True,
                        "route_id": self._find_global_route(
                            "stock_mts_mto_rule.route_mto_mts",
                            _("Make To Order + Make To Stock"),
                        ).id,
                    },
                    "update_values": {
                        "active": self.mto_mts_management,
                        "name": self._format_rulename(
                            location_id, location_dest_id, "MTS+MTO"
                        ),
                        "location_dest_id": location_dest_id.id,
                        "location_src_id": location_id.id,
                        "picking_type_id": picking_type_id.id,
                    },
                },
            }
        )
        return res

    def _create_or_update_global_routes_rules(self):
        res = super(StockWarehouse, self)._create_or_update_global_routes_rules()

        if (
            self.mto_mts_management
            and self.mts_mto_rule_id
            and self.mts_mto_rule_id.action != "split_procurement"
        ):
            # Cannot create or update with the 'split_procurement' action due
            # to constraint and the fact that the constrained rule_ids may
            # not exist during the initial (or really any) calls of
            # _get_global_route_rules_values
            rule = self.env["stock.rule"].search(
                [
                    ("location_dest_id", "=", self.mts_mto_rule_id.location_dest_id.id),
                    ("location_src_id", "=", self.mts_mto_rule_id.location_src_id.id),
                    ("route_id", "=", self.delivery_route_id.id),
                ],
                limit=1,
            )
            self.mts_mto_rule_id.write(
                {
                    "action": "split_procurement",
                    "mts_rule_id": rule.id,
                    "mto_rule_id": self.mto_pull_id.id,
                }
            )
        return res
