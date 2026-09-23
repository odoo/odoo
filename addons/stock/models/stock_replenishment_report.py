from collections import defaultdict

from dateutil import relativedelta

from odoo import SUPERUSER_ID, api, fields, models
from odoo.fields import Domain
from odoo.tools import float_compare

from ..tools import debug_log as dbg


class StockReplenishmentReport(models.AbstractModel):
    _name = "stock.replenishment.report"
    _description = "Replenishment Shortage Scan"

    @dbg.timed
    @api.model
    def _create_missing_orderpoints(self, orderpoints):
        shortages = self._get_projected_shortages()
        dbg.pipeline.debug(
            "replenishment report: %d projected shortages", len(shortages)
        )
        shortages = self._get_net_shortages(shortages, orderpoints)
        dbg.pipeline.debug("replenishment report: %d net shortages", len(shortages))
        return self._create_shortage_orderpoints(shortages, orderpoints)

    @api.model
    def _get_candidate_products(self):
        return self.env["product.product"].search(
            [("is_storable", "=", True), ("stock_move_ids", "!=", False)],
        )

    @api.model
    def _get_replenish_locations(self):
        return self.env["stock.location"].search([("replenish_location", "=", True)])

    @api.model
    def _get_uncovered_quantities(self, products, locations):
        Move = self.env["stock.move"].with_context(active_test=False)
        Quant = self.env["stock.quant"].with_context(active_test=False)
        Location = self.env["stock.location"]
        domain_quant, _dummy, domain_move_out_loc = Location._get_domains_quantity(
            locations.ids,
        )
        domain_state = Domain(
            "state",
            "in",
            ("waiting", "confirmed", "assigned", "partially_available"),
        )
        domain_product = Domain("product_id", "in", products.ids)
        domain_quant = Domain.AND((domain_product, domain_quant))
        domain_move_out = Domain.AND(
            (domain_product, domain_state, domain_move_out_loc),
        )

        replenish_ids = set(locations.ids)
        ancestors_by_location = {}

        def get_replenish_ancestor_ids(location):
            if not location:
                return ()
            ancestors = ancestors_by_location.get(location.id)
            if ancestors is None:
                ancestors = tuple(
                    ancestor_id
                    for ancestor_id in map(
                        int,
                        (location.parent_path or "").split("/")[:-1],
                    )
                    if ancestor_id in replenish_ids
                )
                ancestors_by_location[location.id] = ancestors
            return ancestors

        net_qty = defaultdict(float)
        for product, location, qty in Move._read_group(
            domain_move_out,
            ["product_id", "location_id"],
            ["product_qty:sum"],
        ):
            for replenish_id in get_replenish_ancestor_ids(location):
                net_qty[product, replenish_id] -= qty
        for product, location, qty in Quant._read_group(
            domain_quant,
            ["product_id", "location_id"],
            ["quantity:sum"],
        ):
            for replenish_id in get_replenish_ancestor_ids(location):
                net_qty[product, replenish_id] += qty
        return net_qty

    @dbg.timed
    @api.model
    def _get_projected_shortages(self):
        products = self._get_candidate_products()
        locations = self._get_replenish_locations()
        uncovered = self._get_uncovered_quantities(products, locations)
        dbg.performance.debug(
            "_get_projected_shortages: %d products x %d locations -> %d uncovered keys",
            len(products),
            len(locations),
            len(uncovered),
        )

        location_by_id = {location.id: location for location in locations}
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        extra_routes = products._get_total_routes_by_product()
        rules_cache = {}
        products_by_horizon = defaultdict(set)
        for (product, location_id), quantity in uncovered.items():
            if product.uom_id.compare(quantity, 0) >= 0:
                continue
            location = location_by_id[location_id]
            cache_key = (
                location,
                product.route_ids,
                product.route_ids
                | product.categ_id.total_route_ids
                | extra_routes[product.id],
            )
            rules = rules_cache.get(cache_key)
            if rules is None:
                rules = product._get_rules_from_location(location)
                rules_cache[cache_key] = rules
            lead_days = rules.with_context(
                bypass_delay_description=True,
                global_horizon_days=Orderpoint._get_horizon_days(location.company_id),
            )._get_lead_days(product)[0]
            horizon = lead_days["total_delay"] + lead_days["horizon_time"]
            products_by_horizon[horizon, location].add(product.id)

        end_of_today = fields.Datetime.now().replace(hour=23, minute=59, second=59)
        shortages = {}
        dbg.performance.debug(
            "_get_projected_shortages: %d (horizon, location) forecast reads, %d rule lookups",
            len(products_by_horizon),
            len(rules_cache),
        )
        for (horizon, location), product_ids in products_by_horizon.items():
            candidates = self.env["product.product"].browse(product_ids)
            forecasts = candidates.with_context(
                location=location.id,
                to_date=end_of_today + relativedelta.relativedelta(days=horizon),
            ).read(["qty_available_virtual"])
            products_by_id = {product.id: product for product in candidates}
            for forecast in forecasts:
                product = products_by_id[forecast["id"]]
                quantity = forecast["qty_available_virtual"]
                if product.uom_id.compare(quantity, 0) < 0:
                    shortages[product.id, location.id] = quantity
        return shortages

    @api.model
    def _get_net_shortages(self, shortages, orderpoints):
        if not shortages:
            return shortages
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        product_ids = list({product_id for product_id, _location in shortages})
        location_ids = list({location_id for _product, location_id in shortages})
        in_progress = (
            self.env["product.product"]
            .browse(product_ids)
            ._get_quantity_in_progress(location_ids=location_ids)[0]
        )
        suggested = {
            (product.id, location.id): sum(group.mapped("qty_to_order"))
            for product, location, group in Orderpoint._read_group(
                [("id", "in", orderpoints.ids), ("product_id", "in", product_ids)],
                ["product_id", "location_id"],
                ["id:recordset"],
            )
        }
        precision_digits = self.env["decimal.precision"].get_precision("Product Unit")
        netted = {}
        for key, quantity in shortages.items():
            covered = (in_progress.get(key) or 0.0) + suggested.get(key, 0.0)
            remaining = quantity + covered
            if float_compare(remaining, 0.0, precision_digits=precision_digits) < 0:
                netted[key] = remaining
            else:
                dbg.logic.debug(
                    "shortage %s of %s covered by in-progress/suggested %s",
                    key,
                    quantity,
                    covered,
                )
        return netted

    @api.model
    def _create_shortage_orderpoints(self, shortages, orderpoints):
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        if not shortages:
            return Orderpoint.browse()
        existing = {
            (product.id, location.id)
            for product, location, _group in Orderpoint.with_context(
                active_test=False,
            )._read_group(
                [
                    ("id", "in", orderpoints.ids),
                    (
                        "product_id",
                        "in",
                        list({product_id for product_id, _loc in shortages}),
                    ),
                ],
                ["product_id", "location_id"],
                ["id:recordset"],
            )
        }
        locations = self.env["stock.location"].browse(
            {location_id for _product, location_id in shortages}
        )
        fallback_warehouse = {}
        for warehouse in self.env["stock.warehouse"].search(
            [("company_id", "in", locations.company_id.ids)]
        ):
            fallback_warehouse.setdefault(warehouse.company_id.id, warehouse.id)
        values_list = []
        for product_id, location_id in shortages:
            if (product_id, location_id) in existing:
                continue
            location = self.env["stock.location"].browse(location_id)
            values = Orderpoint._prepare_orderpoint_vals(product_id, location_id)
            values.update(
                {
                    "name": self.env._("Replenishment Report"),
                    "warehouse_id": location.warehouse_id.id
                    or fallback_warehouse.get(location.company_id.id, False),
                    "company_id": location.company_id.id,
                },
            )
            values_list.append(values)
        dbg.lifecycle.debug(
            "_create_shortage_orderpoints: %d new of %d shortages (%d existing)",
            len(values_list),
            len(shortages),
            len(existing),
        )
        return Orderpoint.with_user(SUPERUSER_ID).create(values_list)
