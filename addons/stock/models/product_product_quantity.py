import logging
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, time
from typing import NamedTuple

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import DOMAIN_PREDICATES

from ..tools import debug_log as dbg
from odoo.addons.stock.const import QUANTITY_FIELDS
from odoo.addons.stock.tools.quantity import (
    QuantityFilters,
    get_domain_quantity_in_python,
)

_logger = logging.getLogger(__name__)


class QuantityScope(NamedTuple):
    quant: Domain
    expired_quant: Domain | None
    move_in_todo: Domain
    move_out_todo: Domain
    move_in_done: Domain
    move_out_done: Domain
    dates_in_the_past: bool
    move_in_done_lines: Domain | None = None
    move_out_done_lines: Domain | None = None


class QuantityReads(NamedTuple):
    quants: dict
    expired_unreserved: dict
    moves_in: dict
    moves_out: dict
    moves_in_past: dict
    moves_out_past: dict


class ProductProductQuantity(models.Model):
    _inherit = "product.product"

    @api.depends_context(
        "lot_id",
        "owner_id",
        "owners",
        "package_id",
        "from_date",
        "to_date",
        "location",
        "warehouse_id",
        "search_location",
        "search_warehouse",
        "allowed_company_ids",
        "uid",
        "strict",
        "skip_in_progress",
    )
    @api.depends(
        "stock_move_ids.product_qty",
        "stock_move_ids.state",
        "stock_move_ids.quantity",
        "stock_move_ids.date",
        "stock_move_ids.location_id",
        "stock_move_ids.location_dest_id",
        "stock_move_ids.location_final_id",
        "stock_quant_ids.quantity",
        "stock_quant_ids.reserved_quantity",
        "stock_quant_ids.location_id",
        "stock_quant_ids.lot_id",
        "stock_quant_ids.owner_id",
        "stock_quant_ids.package_id",
    )
    @dbg.timed
    def _compute_quantities(self):
        prefetch_fields = self.env.context.get("prefetch_fields", True)
        guarded = self.with_context(skip_qty_available_update=True)
        products = (
            guarded.with_context(prefetch_fields=False)
            .filtered(lambda p: p.type != "service")
            .with_context(prefetch_fields=prefetch_fields)
        )
        services = guarded - products
        for field_name in QUANTITY_FIELDS:
            services[field_name] = 0.0
        dbg.performance.debug(
            "_compute_quantities: %d products (%d services)",
            len(products),
            len(services),
        )
        if not products:
            return
        res = products._prepare_quantities_vals(QuantityFilters.from_context(self.env))
        for product in products:
            product.update(res[product.id])

    def _inverse_qty_available(self):
        if self.env.context.get("skip_qty_available_update", False):
            return
        self._update_qty_available([product.qty_available for product in self])

    def _update_qty_available(self, quantities):
        product_ids = []
        quantities_to_apply = []
        for product, quantity in zip(self, quantities, strict=True):
            storable = product.type == "consu" and product.is_storable
            if not storable:
                if not quantity:
                    continue
                raise UserError(
                    _(
                        "%(product)s does not track inventory, so it cannot have a"
                        " quantity on hand. Enable Track Inventory first.",
                        product=product.display_name,
                    ),
                )
            if product.tracking != "none":
                raise UserError(
                    _(
                        "%(product)s is tracked by lot/serial number: set its quantity"
                        " through an inventory adjustment so lot/serial numbers can be"
                        " assigned.",
                        product=product.display_name,
                    ),
                )
            if product.uom_id.compare(quantity, 0.0) < 0:
                raise UserError(
                    _(
                        "The quantity on hand of %(product)s cannot be set to a negative value.",
                        product=product.display_name,
                    ),
                )
            product_ids.append(product.id)
            quantities_to_apply.append(quantity)
        if not product_ids:
            return
        products_to_update = self.browse(product_ids)
        scoped_location = self._resolve_inventory_location()
        quantity_by_product = dict(
            zip(products_to_update, quantities_to_apply, strict=True)
        )
        if scoped_location:
            vals_list = [
                {
                    "product_id": product.id,
                    "location_id": scoped_location.id,
                    "inventory_quantity": quantity_by_product[product],
                }
                for product in products_to_update
            ]
        else:
            products_by_company = defaultdict(self.browse)
            for product in products_to_update:
                products_by_company[product.company_id or self.env.company] += product
            warehouses = self.env["stock.warehouse"].search(
                [("company_id", "in", [company.id for company in products_by_company])],
            )
            warehouse_by_company = {}
            for warehouse in warehouses:
                warehouse_by_company.setdefault(warehouse.company_id, warehouse)

            vals_list = []
            for company, products in products_by_company.items():
                warehouse = warehouse_by_company.get(company)
                if not warehouse:
                    self.env["stock.warehouse"].with_company(
                        company
                    )._raise_missing_warehouse()
                    _logger.warning(
                        "Not setting the quantity on hand of %s: company %s has no "
                        "warehouse.",
                        products,
                        company.display_name,
                    )
                    continue
                vals_list += [
                    {
                        "product_id": product.id,
                        "location_id": warehouse.lot_stock_id.id,
                        "inventory_quantity": quantity_by_product[product],
                    }
                    for product in products
                ]
        if not vals_list:
            return
        dbg.pipeline.debug(
            "_update_qty_available: %d inventory quants (scoped location %s)",
            len(vals_list),
            scoped_location.id if scoped_location else None,
        )
        quants = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True, from_inverse_qty=True)
            .create(vals_list)
        )
        quants._apply_inventory()

    def _resolve_inventory_location(self):
        Location = self.env["stock.location"]
        location_ids = Location._resolve_scope_ids_from_context()
        if location_ids is None:
            return Location.browse()
        locations = Location.browse(location_ids)
        warehouses = locations.warehouse_id
        if len(locations) == 1 and locations.usage == "internal":
            return locations
        if len(warehouses) == 1 and locations == warehouses.view_location_id:
            return warehouses.lot_stock_id
        if len(locations) == 1:
            raise UserError(
                _(
                    "The quantity on hand cannot be set while the view is scoped to "
                    "%(location)s: it is not an internal location, so it holds no "
                    "stock of its own. Scope the view to a stock location or a "
                    "warehouse, or use an inventory adjustment.",
                    location=locations.display_name,
                ),
            )
        raise UserError(
            _(
                "The quantity on hand cannot be set while the view is scoped to "
                "%(count)s locations (%(locations)s): the value is a total over all of "
                "them, and there is no way to tell how it should be split. Scope the "
                "view to a single location or warehouse, or use an inventory "
                "adjustment.",
                count=len(locations),
                locations=", ".join(locations.mapped("display_name")[:5]) or "none",
            ),
        )

    def _search_qty_available(self, operator, value):
        filters = QuantityFilters.from_context(self.env)
        op = DOMAIN_PREDICATES.get(operator)
        if (
            op is not None
            and not op(0.0, value)
            and not (filters.from_date or filters.to_date or filters.owners is not None)
        ):
            product_ids = self._get_product_ids_from_quants(operator, value, filters)
            if product_ids is not NotImplemented:
                return [("id", "in", product_ids)]
        return self._get_domain_product_quantity(operator, value, "qty_available")

    def _search_qty_available_virtual(self, operator, value):
        return self._get_domain_product_quantity(
            operator, value, "qty_available_virtual"
        )

    def _search_qty_incoming(self, operator, value):
        return self._get_domain_product_quantity(operator, value, "qty_incoming")

    def _search_qty_outgoing(self, operator, value):
        return self._get_domain_product_quantity(operator, value, "qty_outgoing")

    def _search_qty_free(self, operator, value):
        return self._get_domain_product_quantity(operator, value, "qty_free")

    def _get_quantity_totals(self, field, location_domains=None):
        location_domains = (
            location_domains
            or self.env["stock.location"]._get_domains_quantity_from_context()
        )
        candidates = self._get_quantity_search_candidates(
            location_domains=location_domains
        )
        vals_by_product = candidates.with_context(
            prefetch_fields=False
        )._prepare_quantities_vals(
            QuantityFilters.from_context(self.env),
            location_domains=location_domains,
        )
        totals = {
            product_id: vals[field] for product_id, vals in vals_by_product.items()
        }
        return totals, candidates

    @api.model
    def _get_domain_quantity_search(self, totals, op, operator, value, field):
        matched = [record_id for record_id, total in totals.items() if op(total, value)]
        zero_matches = bool(op(0.0, value))
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(
                "quantity search %s %s %r: %s of %s candidates matched; records "
                "with nothing in scope %s",
                field,
                operator,
                value,
                len(matched),
                len(totals),
                "match too, zero satisfies the operator"
                if zero_matches
                else "do not match",
            )
        if zero_matches:
            return ["|", ("id", "in", matched), ("id", "not in", list(totals))]
        return [("id", "in", matched)]

    def _get_domain_product_quantity(self, operator, value, field):
        op = DOMAIN_PREDICATES.get(operator)
        if op is None:
            return get_domain_quantity_in_python(self, field, operator, value)
        totals, __ = self._get_quantity_totals(field)
        return self._get_domain_quantity_search(totals, op, operator, value, field)

    def _get_product_ids_from_quants(self, operator, value, filters=None):
        op = DOMAIN_PREDICATES.get(operator)
        if not op:
            return NotImplemented
        if isinstance(value, Iterable) and not isinstance(value, str):
            value = {float(v) for v in value}
        else:
            value = float(value)
        if filters is None:
            filters = QuantityFilters.from_context(self.env)

        product_ids = set()
        domain_quant = self._narrow_quantity_domains(
            self.env["stock.location"]._get_domains_quantity_from_context()[0],
            Domain.TRUE,
            Domain.TRUE,
            filters,
        )[0]
        quants_groupby = self.env["stock.quant"]._read_group(
            domain_quant, ["product_id"], ["quantity:sum"]
        )
        for product, quantity_sum in quants_groupby:
            if op(quantity_sum, value):
                product_ids.add(product.id)
        return sorted(product_ids)

    @api.model
    def _is_day_value(self, value):
        return (isinstance(value, date) and not isinstance(value, datetime)) or (
            isinstance(value, str) and len(value) == 10
        )

    @api.model
    def _get_day_edge_in_reader_tz(self, day, edge):
        return (
            datetime.combine(day, edge)
            .replace(tzinfo=self.env.tz)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

    @api.model
    def _normalize_quantities_from_date(self, from_date):
        if not from_date:
            return from_date
        value = fields.Datetime.to_datetime(from_date)
        if self._is_day_value(from_date):
            return self._get_day_edge_in_reader_tz(value.date(), time.min)
        return value

    @api.model
    def _normalize_quantities_to_date(self, to_date):
        value = fields.Datetime.to_datetime(to_date)
        if self._is_day_value(to_date):
            value = self._get_day_edge_in_reader_tz(value.date(), time.max)
        return value, bool(value and value < fields.Datetime.now())

    def _narrow_quantity_domains(self, quant, move_in, move_out, filters):
        lot_id, owner_id, package_id = (
            filters.lot_id,
            filters.owner_id,
            filters.package_id,
        )
        if lot_id is not None:
            quant &= Domain([("lot_id", "=", lot_id)])
            move_in &= Domain([("move_line_ids.lot_id", "=", lot_id)])
            move_out &= Domain([("move_line_ids.lot_id", "=", lot_id)])
        if owner_id is not None:
            quant &= Domain([("owner_id", "=", owner_id)])
            move_in &= Domain([("restrict_partner_id", "=", owner_id)])
            move_out &= Domain([("restrict_partner_id", "=", owner_id)])
        if filters.owners is not None:
            owner_leaf = ("in", filters.owners) if filters.owners else ("=", False)
            quant &= Domain([("owner_id", *owner_leaf)])
            move_in &= Domain([("move_line_ids.owner_id", *owner_leaf)])
            move_out &= Domain([("move_line_ids.owner_id", *owner_leaf)])
        if package_id is not None:
            quant &= Domain([("package_id", "=", package_id)])
            move_in &= Domain([("move_line_ids.result_package_id", "=", package_id)])
            move_out &= Domain([("move_line_ids.package_id", "=", package_id)])
        return quant, move_in, move_out

    def _get_domains_quantity_leaves(self, filters):
        in_leaves = Domain.TRUE
        out_leaves = Domain.TRUE
        narrowed = False
        if filters.lot_id is not None:
            leaf = Domain([("lot_id", "=", filters.lot_id)])
            in_leaves &= leaf
            out_leaves &= leaf
            narrowed = True
        if filters.owners is not None:
            owner_leaf = ("in", filters.owners) if filters.owners else ("=", False)
            leaf = Domain([("owner_id", *owner_leaf)])
            in_leaves &= leaf
            out_leaves &= leaf
            narrowed = True
        if filters.package_id is not None:
            in_leaves &= Domain([("result_package_id", "=", filters.package_id)])
            out_leaves &= Domain([("package_id", "=", filters.package_id)])
            narrowed = True
        if not narrowed:
            return None, None
        return in_leaves, out_leaves

    def _prepare_quantities_scope(self, filters, location_domains=None):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = (
            location_domains
            or self.env["stock.location"]._get_domains_quantity_from_context()
        )
        product_domain = Domain([("product_id", "in", self.ids)])
        domain_quant = product_domain & domain_quant_loc
        from_date = self._normalize_quantities_from_date(filters.from_date)
        to_date, dates_in_the_past = self._normalize_quantities_to_date(filters.to_date)

        domain_move_in = product_domain & domain_move_in_loc
        domain_move_out = product_domain & domain_move_out_loc
        domain_quant, domain_move_in, domain_move_out = self._narrow_quantity_domains(
            domain_quant,
            domain_move_in,
            domain_move_out,
            filters,
        )
        domain_move_in_done = domain_move_in
        domain_move_out_done = domain_move_out
        if from_date:
            date_domain_from = Domain([("date", ">=", from_date)])
            domain_move_in &= date_domain_from
            domain_move_out &= date_domain_from
        if to_date:
            date_domain_to = Domain([("date", "<=", to_date)])
            domain_move_in &= date_domain_to
            domain_move_out &= date_domain_to
        state_todo = Domain(
            [
                (
                    "state",
                    "in",
                    ("waiting", "confirmed", "assigned", "partially_available"),
                ),
            ]
        )
        expired_quant = self._get_expired_quant_domain_at_date(domain_quant, to_date)
        domain_move_in_done_lines = domain_move_out_done_lines = None
        if dates_in_the_past:
            state_done_future = Domain([("state", "=", "done"), ("date", ">", to_date)])
            domain_move_in_done = state_done_future & domain_move_in_done
            domain_move_out_done = state_done_future & domain_move_out_done
            in_leaves, out_leaves = self._get_domains_quantity_leaves(filters)
            if in_leaves is not None:
                domain_move_in_done_lines = (
                    Domain([("move_id", "any", domain_move_in_done)]) & in_leaves
                )
                domain_move_out_done_lines = (
                    Domain([("move_id", "any", domain_move_out_done)]) & out_leaves
                )
        else:
            domain_move_in_done = domain_move_out_done = Domain.FALSE
        dbg.logic.debug(
            "_prepare_quantities_scope: %d products from=%s to=%s past=%s",
            len(self),
            from_date,
            to_date,
            dates_in_the_past,
        )
        return QuantityScope(
            quant=domain_quant,
            expired_quant=expired_quant,
            move_in_todo=state_todo & domain_move_in,
            move_out_todo=state_todo & domain_move_out,
            move_in_done=domain_move_in_done,
            move_out_done=domain_move_out_done,
            dates_in_the_past=dates_in_the_past,
            move_in_done_lines=domain_move_in_done_lines,
            move_out_done_lines=domain_move_out_done_lines,
        )

    def _get_expired_quant_domain_at_date(self, domain_quant, to_date):
        pass

    def _read_quantities(self, scope):
        Move = self.env["stock.move"]
        Quant = self.env["stock.quant"]
        moves_in_res = {
            product.id: product_qty
            for product, product_qty in Move._read_group(
                scope.move_in_todo,
                ["product_id"],
                ["product_qty:sum"],
            )
        }
        moves_out_res = {
            product.id: product_qty
            for product, product_qty in Move._read_group(
                scope.move_out_todo,
                ["product_id"],
                ["product_qty:sum"],
            )
        }
        quants_res = {
            product.id: (quantity, reserved_quantity)
            for product, quantity, reserved_quantity in Quant._read_group(
                scope.quant,
                ["product_id"],
                ["quantity:sum", "reserved_quantity:sum"],
            )
        }
        expired_unreserved_quants_res = {}
        if scope.expired_quant is not None:
            expired_unreserved_quants_res = {
                product.id: quantity - reserved_quantity
                for product, quantity, reserved_quantity in Quant._read_group(
                    scope.expired_quant,
                    ["product_id"],
                    ["quantity:sum", "reserved_quantity:sum"],
                )
            }
        moves_in_res_past, moves_out_res_past = self._read_past_quantities(scope)
        reads = QuantityReads(
            quants=quants_res,
            expired_unreserved=expired_unreserved_quants_res,
            moves_in=moves_in_res,
            moves_out=moves_out_res,
            moves_in_past=moves_in_res_past,
            moves_out_past=moves_out_res_past,
        )
        self._log_quantity_reads(reads)
        return reads

    def _read_past_quantities(self, scope):
        moves_in_res_past = defaultdict(float)
        moves_out_res_past = defaultdict(float)
        if scope.dates_in_the_past and scope.move_in_done_lines is not None:
            MoveLine = self.env["stock.move.line"]
            for target, domain in (
                (moves_in_res_past, scope.move_in_done_lines),
                (moves_out_res_past, scope.move_out_done_lines),
            ):
                for product, quantity in MoveLine._read_group(  # noqa: E8507 - two literal branches, not one query per record
                    domain, ["product_id"], ["quantity_product_uom:sum"]
                ):
                    target[product.id] += quantity
        elif scope.dates_in_the_past:
            Move = self.env["stock.move"]
            groupby = ["product_id", "product_uom_id"]
            past_in = Move._read_group(scope.move_in_done, groupby, ["quantity:sum"])
            past_out = Move._read_group(scope.move_out_done, groupby, ["quantity:sum"])
            for target, groups in (
                (moves_in_res_past, past_in),
                (moves_out_res_past, past_out),
            ):
                for product, uom, quantity in groups:
                    target[product.id] += uom._get_quantity_in_unit(
                        quantity,
                        product.uom_id,
                    )
        return moves_in_res_past, moves_out_res_past

    def _log_quantity_reads(self, reads):
        if not _logger.isEnabledFor(logging.DEBUG):
            return
        for product in self:
            pid = product._origin.id
            quantity, reserved = reads.quants.get(pid, (0.0, 0.0))
            _logger.debug(
                "quantities product=%s: quant=%s reserved=%s expired=%s "
                "in=%s out=%s past_in=%s past_out=%s",
                pid,
                quantity,
                reserved,
                reads.expired_unreserved.get(pid, 0.0),
                reads.moves_in.get(pid, 0.0),
                reads.moves_out.get(pid, 0.0),
                reads.moves_in_past.get(pid, 0.0),
                reads.moves_out_past.get(pid, 0.0),
            )

    @dbg.timed
    def _prepare_quantities_vals(self, filters, location_domains=None):
        scope = self._prepare_quantities_scope(
            filters, location_domains=location_domains
        )
        with dbg.timer(self.env, "_read_quantities for %d products", len(self)):
            reads = self._read_quantities(scope)
        res = {}

        for product in self.with_context(prefetch_fields=False):
            origin_product_id = product._origin.id
            product_id = product.id
            res[product_id] = {}
            quantity, reserved_quantity = reads.quants.get(
                origin_product_id, (0.0, 0.0)
            )
            qty_available = quantity
            if scope.dates_in_the_past:
                qty_available += reads.moves_out_past.get(
                    origin_product_id, 0.0
                ) - reads.moves_in_past.get(origin_product_id, 0.0)
            expired_unreserved_qty = reads.expired_unreserved.get(
                origin_product_id,
                0.0,
            )
            res[product_id]["qty_available"] = product.uom_id._round_aggregate(
                qty_available
            )
            res[product_id]["qty_free"] = product.uom_id._round_aggregate(
                qty_available - reserved_quantity - expired_unreserved_qty
            )
            res[product_id]["qty_incoming"] = product.uom_id._round_aggregate(
                reads.moves_in.get(origin_product_id, 0.0),
            )
            res[product_id]["qty_outgoing"] = product.uom_id._round_aggregate(
                reads.moves_out.get(origin_product_id, 0.0),
            )
            res[product_id]["qty_available_virtual"] = product.uom_id._round_aggregate(
                qty_available
                + res[product_id]["qty_incoming"]
                - res[product_id]["qty_outgoing"]
                - expired_unreserved_qty,
            )

        return res

    def _get_quantity_search_candidates(self, location_domains=None):
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = (
            location_domains
            or self.env["stock.location"]._get_domains_quantity_from_context()
        )
        Quant = self.env["stock.quant"]
        Move = self.env["stock.move"]
        product_ids = {
            product.id
            for [product] in Quant._read_group(domain_quant_loc, ["product_id"])
        }
        product_ids |= {
            product.id
            for [product] in Move._read_group(
                (domain_move_in_loc | domain_move_out_loc)
                & Domain("state", "not in", ("draft", "cancel")),
                ["product_id"],
            )
        }
        dbg.performance.debug(
            "_get_quantity_search_candidates: %d products with stock data",
            len(product_ids),
        )
        return self.env["product.product"].browse(product_ids)
