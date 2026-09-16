import logging
from collections import defaultdict
from typing import NamedTuple

from odoo import api, models
from odoo.fields import Domain
from odoo.libs.numbers import float_compare

from ..const import CONTEXT_PUTAWAY_SCAN
from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class PutawayCapacity(NamedTuple):
    forecast_weight: dict
    foreign_inbound_ids: frozenset
    package_weight: float


class PutawayScan:
    def __init__(self, product, placed=None):
        self.product = product
        self.placed = defaultdict(float, placed or {})
        self.staged = defaultdict(float)
        self._memo = {}

    def memo(self, key, factory):
        if key not in self._memo:
            self._memo[key] = factory()
        return self._memo[key]

    def place(self, location, quantity):
        self.placed[location.id] += quantity
        self.staged[location.id] += quantity

    def get_staged_weight(self, location_id):
        return self.staged.get(location_id, 0.0) * self.product.weight


class StockLocationPutaway(models.Model):
    _inherit = "stock.location"

    def _filtered_putaway_access(self):
        return self

    @dbg.timed
    def _get_putaway_strategy(
        self, product, quantity=0, package=None, packaging=None, additional_qty=None
    ):
        self.check_singleton()
        destination = self._filtered_putaway_access()
        products = self.env.context.get("products", self.env["product.product"])
        products |= product
        package_type = self.env["stock.package.type"]
        if package:
            package_type = package.package_type_id
        elif packaging:
            package_type = packaging.package_type_id

        leaf_category = (
            products.categ_id
            if len(products.categ_id) == 1
            else self.env["product.category"]
        )
        category_ancestors = leaf_category.browse(
            map(int, (leaf_category.parent_path or "").split("/")[:-1])
        )

        putaway_rules = destination.putaway_rule_ids.filtered(
            lambda rule: (
                (not rule.product_id or rule.product_id in products)
                and (not rule.category_id or rule.category_id in category_ancestors)
                and (not rule.package_type_ids or package_type in rule.package_type_ids)
            )
        )

        putaway_rules = putaway_rules.sorted(
            lambda rule: (
                bool(rule.package_type_ids),
                bool(rule.product_id),
                bool(rule.category_id == leaf_category),
                bool(rule.category_id),
            ),
            reverse=True,
        )

        putaway_location = None
        locations = self.env.context.get("locations")
        if locations is None:
            locations = destination.child_internal_location_ids
        else:
            locations = locations.filtered(
                lambda loc, parent=destination: loc._is_child_of(parent),
            )
        if putaway_rules:
            qty_by_location = destination._get_putaway_qty_by_location(
                product, package, package_type, locations, additional_qty
            )
            putaway_location = putaway_rules._get_putaway_location(
                product, quantity, package, packaging, qty_by_location
            )

        from_rule = bool(putaway_location)
        if not putaway_location:
            putaway_location = (
                locations[0]
                if locations and destination.usage == "view"
                else destination
            )

        dbg.logic.debug(
            "[location:%s] putaway product=%s qty=%s package_type=%s: %d rules, "
            "%d candidate locations -> %s (%s)",
            self.id,
            product.id,
            quantity,
            package_type.id,
            len(putaway_rules),
            len(locations),
            putaway_location.id,
            "rule" if from_rule else "default",
        )
        return putaway_location

    @dbg.timed
    def _get_putaway_strategy_batch(
        self, product, quantities, package=None, packaging=None, additional_qty=None
    ):
        self.check_singleton()
        dbg.performance.debug(
            "[location:%s] _get_putaway_strategy_batch: %d quantities",
            self.id,
            len(quantities),
        )
        scan = PutawayScan(product, additional_qty)
        scanner = self.with_context(**{CONTEXT_PUTAWAY_SCAN: scan})
        locations = []
        for quantity in quantities:
            location = scanner._get_putaway_strategy(
                product,
                quantity,
                package=package,
                packaging=packaging,
                additional_qty=scan.placed,
            )
            scan.place(location, quantity)
            locations.append(location._with_putaway_scan_cleared())
        return locations

    def _with_putaway_scan_cleared(self):
        return self.with_context(
            {
                key: value
                for key, value in self.env.context.items()
                if key != CONTEXT_PUTAWAY_SCAN
            },
        )

    def _memoize_putaway(self, key, factory):
        scan = self.env.context.get(CONTEXT_PUTAWAY_SCAN)
        if scan is None:
            return factory()
        return scan.memo(key, factory)

    def _get_putaway_qty_by_location(
        self, product, package, package_type, locations, additional_qty=None
    ):
        qty_by_location = defaultdict(
            float,
            self._get_stored_putaway_qty(product, package, package_type, locations),
        )
        for location_id, qty in (additional_qty or {}).items():
            qty_by_location[location_id] += qty
        return qty_by_location

    def _get_stored_putaway_qty(self, product, package, package_type, locations):
        if not locations.storage_category_id:
            return {}
        by_package = bool(package and package.package_type_id)
        exclude_sml_ids = list(self.env.context.get("exclude_sml_ids", set()))
        return self._memoize_putaway(
            (
                "stored_qty",
                by_package,
                package_type.id,
                product.id,
                tuple(locations.ids),
                tuple(sorted(exclude_sml_ids)),
            ),
            lambda: (
                self._get_putaway_package_count_by_location(
                    package_type, locations, exclude_sml_ids
                )
                if by_package
                else self._get_putaway_product_qty_by_location(
                    product, locations, exclude_sml_ids
                )
            ),
        )

    def _get_putaway_package_count_by_location(
        self, package_type, locations, exclude_sml_ids
    ):
        count_by_location = defaultdict(int)
        move_line_data = self.env["stock.move.line"]._read_group(
            [
                ("id", "not in", exclude_sml_ids),
                ("result_package_id.package_type_id", "=", package_type.id),
                ("state", "not in", ["draft", "done", "cancel"]),
                ("location_dest_id", "in", locations.ids),
            ],
            ["location_dest_id"],
            ["result_package_id:count_distinct"],
        )
        for location_dest, count in move_line_data:
            count_by_location[location_dest.id] += count
        quant_data = self.env["stock.quant"]._read_group(
            [
                ("package_id.package_type_id", "=", package_type.id),
                ("location_id", "in", locations.ids),
            ],
            ["location_id"],
            ["package_id:count_distinct"],
        )
        for location, count in quant_data:
            count_by_location[location.id] += count
        return count_by_location

    def _get_putaway_product_qty_by_location(self, product, locations, exclude_sml_ids):
        qty_by_location = defaultdict(float)
        quant_data = self.env["stock.quant"]._read_group(
            [
                ("product_id", "=", product.id),
                ("location_id", "in", locations.ids),
            ],
            ["location_id"],
            ["quantity:sum"],
        )
        for location, quantity_sum in quant_data:
            qty_by_location[location.id] += quantity_sum
        move_line_data = self.env["stock.move.line"]._read_group(
            [
                ("id", "not in", exclude_sml_ids),
                ("product_id", "=", product.id),
                ("location_dest_id", "in", locations.ids),
                ("state", "not in", ["draft", "done", "cancel"]),
            ],
            ["location_dest_id"],
            ["quantity:array_agg", "product_uom_id:array_agg"],
        )
        for location_dest, quantity_list, uom_ids in move_line_data:
            uoms = self.env["uom.uom"].browse(uom_ids)
            current_qty = sum(
                uom._get_quantity_in_unit(float(qty), product.uom_id)
                for qty, uom in zip(quantity_list, uoms, strict=True)
            )
            qty_by_location[location_dest.id] += current_qty
        return qty_by_location

    def _get_effective_product(self, product):
        return (
            product or self.env.context.get("products") or self.env["product.product"]
        )

    def _get_putaway_capacity(self, product, package=None):
        if not self:
            return PutawayCapacity({}, frozenset(), 0.0)
        stored = self._memoize_putaway(
            (
                "capacity",
                product.id,
                package.id if package else 0,
                tuple(self.ids),
                tuple(sorted(self.env.context.get("exclude_sml_ids", set()))),
            ),
            lambda: self._get_stored_putaway_capacity(product, package),
        )
        scan = self.env.context.get(CONTEXT_PUTAWAY_SCAN)
        if scan is None:
            return stored
        return stored._replace(
            forecast_weight={
                location_id: stored.forecast_weight.get(location_id, 0.0)
                + scan.get_staged_weight(location_id)
                for location_id in self.ids
            },
        )

    def _get_stored_putaway_capacity(self, product, package):
        weight_by_location = self._get_weight(
            self.env.context.get("exclude_sml_ids", set()),
        )
        return PutawayCapacity(
            forecast_weight={
                location.id: weights["forecast_weight"]
                for location, weights in weight_by_location.items()
            },
            foreign_inbound_ids=frozenset(
                self._get_foreign_inbound_location_ids(
                    self, self._get_effective_product(product)
                ),
            ),
            package_weight=self._get_package_weight(package),
        )

    @api.model
    def _get_package_weight(self, package):
        if not package:
            return 0.0
        package_smls = self.env["stock.move.line"].search(
            [
                ("result_package_id", "=", package.id),
                ("state", "not in", ["done", "cancel"]),
            ],
        )
        return sum(
            package_smls.mapped(
                lambda sml: sml.quantity_product_uom * sml.product_id.weight,
            ),
        )

    def _get_weight(self, exclude_sml_ids=None):
        exclude_sml_ids = exclude_sml_ids or set()
        Product = self.env["product.product"]
        StockMoveLine = self.env["stock.move.line"]

        quants = self.env["stock.quant"]._read_group(
            [("location_id", "in", self.ids)],
            groupby=["location_id", "product_id"],
            aggregates=["quantity:sum"],
        )
        base_domain = Domain("state", "not in", ["draft", "done", "cancel"]) & Domain(
            "id",
            "not in",
            tuple(exclude_sml_ids),
        )
        outgoing_move_lines = StockMoveLine._read_group(
            Domain("location_id", "in", self.ids) & base_domain,
            groupby=["location_id", "product_id"],
            aggregates=["quantity_product_uom:sum"],
        )
        incoming_move_lines = StockMoveLine._read_group(
            Domain("location_dest_id", "in", self.ids) & base_domain,
            groupby=["location_dest_id", "product_id"],
            aggregates=["quantity_product_uom:sum"],
        )

        products = Product.union(
            *(
                product
                for __, product, __ in quants
                + outgoing_move_lines
                + incoming_move_lines
            ),
        )
        products.fetch(["weight"])

        weight_by_location = defaultdict(lambda: defaultdict(float))
        for loc, product, quantity_sum in quants:
            weight = quantity_sum * product.weight
            weight_by_location[loc]["net_weight"] += weight
            weight_by_location[loc]["forecast_weight"] += weight

        for loc, product, quantity_product_uom_sum in outgoing_move_lines:
            weight_by_location[loc]["forecast_weight"] -= (
                quantity_product_uom_sum * product.weight
            )

        for dest_loc, product, quantity_product_uom_sum in incoming_move_lines:
            weight_by_location[dest_loc]["forecast_weight"] += (
                quantity_product_uom_sum * product.weight
            )

        return weight_by_location

    def _can_be_used(
        self,
        product,
        quantity=0,
        package=None,
        location_qty=0,
        capacity=None,
    ):
        self.check_singleton()
        if not self.storage_category_id:
            return True
        if capacity is None:
            capacity = self._get_putaway_capacity(product, package)
        if not self._can_store_new_product(
            product, package, capacity.foreign_inbound_ids
        ):
            dbg.logic.debug(
                "[location:%s] _can_be_used: refuses new product %s (policy %s)",
                self.id,
                product.id,
                self.storage_category_id.allow_new_product,
            )
            return False
        forecast_weight = capacity.forecast_weight.get(self.id, 0.0)
        if package and package.package_type_id:
            usable = self._can_store_package(
                package, location_qty, forecast_weight, capacity.package_weight
            )
        else:
            usable = self._can_store_product(
                product, quantity, location_qty, forecast_weight
            )
        dbg.logic.debug(
            "[location:%s] _can_be_used product=%s qty=%s at %s forecast_weight=%s -> %s",
            self.id,
            product.id,
            quantity,
            location_qty,
            forecast_weight,
            usable,
        )
        return usable

    def _can_store_new_product(self, product, package, foreign_inbound_ids=None):
        self.check_singleton()
        policy = self.storage_category_id.allow_new_product
        if policy not in ("empty", "same"):
            return True
        positive_quant = self.quant_ids.filtered(
            lambda q: q.product_id.uom_id.compare(q.quantity, 0) > 0,
        )
        if policy == "empty":
            return not positive_quant
        product = self._get_effective_product(product)
        if (positive_quant and positive_quant.product_id != product) or len(
            product
        ) > 1:
            return False
        if foreign_inbound_ids is None:
            foreign_inbound_ids = self._get_foreign_inbound_location_ids(self, product)
        return self.id not in foreign_inbound_ids

    @api.model
    def _get_foreign_inbound_location_ids(self, locations, products):
        return {
            location.id
            for (location,) in self.env["stock.move.line"]._read_group(
                [
                    ("product_id", "not in", products.ids),
                    ("state", "not in", ("done", "cancel")),
                    ("location_dest_id", "in", locations.ids),
                ],
                ["location_dest_id"],
            )
        }

    def _has_weight_capacity(self, added_weight, forecast_weight):
        self.check_singleton()
        max_weight = self.storage_category_id.max_weight
        if not max_weight:
            return True
        weight_precision = self.env["decimal.precision"].get_precision("Stock Weight")
        return (
            float_compare(
                forecast_weight + added_weight,
                max_weight,
                precision_digits=weight_precision,
            )
            <= 0
        )

    def _can_store_package(
        self, package, location_qty, forecast_weight, package_weight=None
    ):
        self.check_singleton()
        storage_category = self.storage_category_id
        if package_weight is None:
            package_weight = self._get_package_weight(package)
        if not self._has_weight_capacity(package_weight, forecast_weight):
            return False
        package_capacity = storage_category.package_capacity_ids.filtered(
            lambda pc: pc.package_type_id == package.package_type_id
        )
        if not package_capacity:
            return True
        qty_precision = self.env["decimal.precision"].get_precision("Product Unit")
        return (
            float_compare(
                location_qty,
                package_capacity.quantity,
                precision_digits=qty_precision,
            )
            < 0
        )

    def _can_store_product(self, product, quantity, location_qty, forecast_weight):
        self.check_singleton()
        storage_category = self.storage_category_id
        if not self._has_weight_capacity(product.weight * quantity, forecast_weight):
            return False
        product_capacity = storage_category.product_capacity_ids.filtered(
            lambda pc: pc.product_id == product,
        )
        if not product_capacity:
            return True
        if product.uom_id.compare(location_qty, product_capacity.quantity) >= 0:
            return False
        return (
            product.uom_id.compare(quantity + location_qty, product_capacity.quantity)
            <= 0
        )

    @api.depends(
        "outgoing_move_line_ids.quantity_product_uom",
        "incoming_move_line_ids.quantity_product_uom",
        "outgoing_move_line_ids.state",
        "incoming_move_line_ids.state",
        "outgoing_move_line_ids.product_id.weight",
        "incoming_move_line_ids.product_id.weight",
        "quant_ids.quantity",
        "quant_ids.product_id.weight",
    )
    def _compute_weight(self):
        weight_by_location = self._get_weight()
        for location in self:
            location.net_weight = weight_by_location[location]["net_weight"]
            location.forecast_weight = weight_by_location[location]["forecast_weight"]
