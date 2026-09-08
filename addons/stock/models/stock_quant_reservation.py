import logging
import math
from decimal import Decimal

from psycopg import Error

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL

from ..const import (
    CONTEXT_BLOCK_EXCLUDED_TYPES,
    get_internal_payload,
    read_internal_payload,
)
from ..tools import debug_log as dbg
from ..tools.reservation import (
    QuantsCache,
    RemovalStrategy,
    ReservationCandidate,
    distribute_reservation,
    get_least_packages,
)
from .stock_quant import CORE_REMOVAL_STRATEGIES

_logger = logging.getLogger(__name__)
LOCKED_QUANTS_CACHE_KEY = "stock.quant.locked"


class StockQuantReservation(models.Model):
    _inherit = "stock.quant"

    @api.model
    def _get_removal_strategy(self, product_id, location_id):
        product_id = product_id.sudo()
        if product_id.categ_id.removal_strategy_id:
            return product_id.categ_id.removal_strategy_id.with_context(
                lang=None
            ).method
        location_id = location_id.sudo()
        if location_id.parent_path:
            ancestor_ids = list(location_id._get_ancestor_ids(include_self=True))
            for loc in self.env["stock.location"].browse(ancestor_ids[::-1]):
                if loc.removal_strategy_id:
                    return loc.removal_strategy_id.with_context(lang=None).method
        else:
            loc = location_id
            while loc:
                if loc.removal_strategy_id:
                    return loc.removal_strategy_id.with_context(lang=None).method
                loc = loc.location_id
        return "fifo"

    @api.model
    def _get_removal_strategies(self):
        return dict(CORE_REMOVAL_STRATEGIES)

    @api.model
    def _get_removal_strategy_record(self, removal_strategy):
        strategy = self._get_removal_strategies().get(removal_strategy)
        if strategy is not None:
            return strategy
        sorted_arguments = self._get_removal_strategy_sort_key(removal_strategy)
        order = self._get_removal_strategy_order(removal_strategy)
        if sorted_arguments is None:
            return RemovalStrategy(order=order)
        sort_key, reverse = sorted_arguments
        return RemovalStrategy(order=order, sort_key=sort_key, reverse=reverse)

    @api.model
    def _get_removal_strategy_order(self, removal_strategy):
        strategy = self._get_removal_strategies().get(removal_strategy)
        if strategy is None:
            raise UserError(_("Removal strategy %s not implemented.", removal_strategy))
        return strategy.order

    @api.model
    def _get_removal_strategy_sort_key(self, removal_strategy):
        strategy = self._get_removal_strategies().get(removal_strategy)
        return strategy.resolve_sorted_arguments() if strategy else None

    def _run_least_packages_removal_strategy_astar(self, domain, qty):
        domain = Domain(domain).optimize(self)
        query = self._search(domain, bypass_access=True)
        query.groupby = SQL("package_id")
        query.having = SQL("SUM(quantity - reserved_quantity) > 0")
        query.order = SQL("available_qty DESC")
        qty_by_package = self.env.execute_query(
            query.select(
                "package_id", "SUM(quantity - reserved_quantity) AS available_qty"
            )
        )

        real_packages = []
        singles_count = 0
        for package_id, available_qty in qty_by_package:
            if package_id is None:
                singles_count += math.ceil(available_qty)
            else:
                real_packages.append((package_id, available_qty))
        singles_count = min(singles_count, math.ceil(qty))
        dbg.logic.debug(
            "least_packages: qty=%s, %d packages, %d singles",
            qty,
            len(real_packages),
            singles_count,
        )

        if not real_packages:
            return domain

        try:
            heavier = [pkg for pkg in real_packages if pkg[1] >= 1]
            lighter = [pkg for pkg in real_packages if pkg[1] < 1]
            qty_by_package = heavier + [(None, 1)] * singles_count + lighter
            with dbg.timer(self.env, "get_least_packages(%d)", len(qty_by_package)):
                taken_packages = get_least_packages(qty_by_package, qty)
            dbg.logic.debug("least_packages: taken %s", taken_packages)
            return self._get_domain_least_packages(taken_packages, domain)
        except MemoryError:
            _logger.info(
                "Ran out of memory while trying to use the least_packages strategy to get quants. Domain: %s",
                domain,
            )
            return domain

    def _get_domain_least_packages(self, taken_packages, domain):
        single_count = sum(1 for pkg in taken_packages if pkg[0] is None)
        selected_single_items = []
        if single_count:
            for quant in self.search(
                Domain("package_id", "=", False) & domain, order="in_date, id"
            ):
                if single_count <= 0:
                    break
                available = quant.quantity - quant.reserved_quantity
                if available <= 0:
                    continue
                selected_single_items.append(quant.id)
                single_count -= available

        return (
            Domain(
                "package_id",
                "in",
                [pkg[0] for pkg in taken_packages if pkg[0] is not None],
            )
            | Domain("id", "in", selected_single_items)
        ) & domain

    def _get_domain_gather(
        self,
        product_id,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
    ):
        domains = [Domain("product_id", "=", product_id.id)]
        if not strict:
            if lot_id:
                domains.append(Domain("lot_id", "in", [lot_id.id, False]))
            if package_id:
                domains.append(Domain("package_id", "=", package_id.id))
            if owner_id:
                domains.append(Domain("owner_id", "=", owner_id.id))
            domains.append(Domain("location_id", "child_of", location_id.id))
        else:
            domains.extend(
                (
                    Domain("lot_id", "in", [False, lot_id.id] if lot_id else [False]),
                    Domain("package_id", "=", package_id.id if package_id else False),
                    Domain("owner_id", "=", owner_id.id if owner_id else False),
                    Domain("location_id", "=", location_id.id),
                ),
            )
        domains.append(self._get_domain_expiration())
        excluded = self._get_block_types_excluded()
        if excluded is None:
            excluded = self.env[
                "stock.location"
            ]._get_block_types_excluded_from_gathering()
        if excluded:
            domains.append(
                Domain("location_id.effective_block_type", "not in", excluded),
            )
        return Domain.AND(domains)

    def _with_block_gather_context(self, reserving=False):
        if self._get_block_types_excluded() is not None:
            return self
        excluded = self.env["stock.location"]._get_block_types_excluded_from_gathering(
            reserving=reserving,
        )
        return self.with_context(
            **{CONTEXT_BLOCK_EXCLUDED_TYPES: get_internal_payload(excluded)},
        )

    def _get_block_types_excluded(self):
        return read_internal_payload(self.env.context, CONTEXT_BLOCK_EXCLUDED_TYPES)

    def _get_domain_expiration(self):
        return Domain.TRUE

    def _filtered_not_expired(self):
        return self

    def _filter_not_blocked(self, quants):
        # the gather domain's block exclusion, read from the gathering
        # environment and applied to quants the cache holds under its own
        excluded = self._get_block_types_excluded()
        if excluded is None:
            excluded = self.env[
                "stock.location"
            ]._get_block_types_excluded_from_gathering()
        if not excluded:
            return quants
        return quants.filtered(
            lambda quant: quant.location_id.effective_block_type not in excluded
        )

    def _gather(
        self,
        product_id,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
        qty=0,
    ):
        removal_strategy = self.env.context.get(
            "_gather_removal_strategy"
        ) or self._get_removal_strategy(product_id, location_id)
        domain = self._get_domain_gather(
            product_id,
            location_id,
            lot_id,
            package_id,
            owner_id,
            strict,
        )

        strategy = self._get_removal_strategy_record(removal_strategy)

        if strategy.narrows_to_packages and qty:
            domain = self._run_least_packages_removal_strategy_astar(domain, qty)

        quants_cache = self.env.context.get("quants_cache")
        cache_sort = strategy.resolve_sorted_arguments()

        from_cache = (
            quants_cache is not None
            and not strategy.narrows_to_packages
            and cache_sort is not None
            and quants_cache.is_covering(product_id, location_id, lot_id)
            and not self._is_gather_domain_extended(
                domain, product_id, location_id, lot_id, package_id, owner_id, strict
            )
        )
        dbg.logic.debug(
            "_gather product=%s location=%s lot=%s strict=%s strategy=%s cache=%s",
            product_id.id,
            location_id.id,
            lot_id.id if lot_id else None,
            strict,
            removal_strategy,
            "hit" if from_cache else ("miss" if quants_cache is not None else "none"),
        )
        if from_cache:
            package_key = package_id.id if package_id else False
            owner_key = owner_id.id if owner_id else False
            if strict:
                res = self.env["stock.quant"]
                if lot_id:
                    res |= quants_cache[
                        product_id.id, location_id.id, lot_id.id, package_key, owner_key
                    ]
                res |= quants_cache[
                    product_id.id, location_id.id, False, package_key, owner_key
                ]
            else:
                # the cache holds every quant under the loaded locations: a
                # non-strict gather reads its subtree from it as the strict
                # one reads its exact key
                res = quants_cache.under(
                    product_id.id,
                    location_id.parent_path or "",
                    lot_id.id if lot_id else False,
                    package_key,
                    owner_key,
                )
            res = self._filter_not_blocked(res._filtered_not_expired())
            sort_key, sort_reverse = cache_sort
            res = res.sorted(sort_key, reverse=sort_reverse)
        else:
            with dbg.timer(self.env, "_gather search product=%s", product_id.id):
                res = self.search(domain, order=strategy.order)

        if strategy.sorts_by_location:
            res = res.sorted(lambda q: (q.location_id.complete_name, -q.id))

        dbg.logic.debug("_gather -> %s", dbg.rec(res))
        return res._sorted_tracked_first()

    def _is_gather_domain_extended(
        self, domain, product_id, location_id, lot_id, package_id, owner_id, strict
    ):
        return domain != type(self)._get_domain_gather(
            self, product_id, location_id, lot_id, package_id, owner_id, strict
        )

    def _filtered_breaking_a_package(self):
        selected = set(self.ids)
        return self.filtered(
            lambda quant: not set(quant.package_id.quant_ids.ids) <= selected
        )

    def _sorted_tracked_first(self):
        return self.sorted(lambda quant: not quant.lot_id)

    @dbg.timed
    def _get_quants_by_products_locations(
        self, product_ids, location_ids, extra_domain=False, lot_scope=None
    ):
        res = QuantsCache(
            self.env["stock.quant"],
            product_ids.ids,
            location_ids.mapped("parent_path"),
            lot_scope=lot_scope.ids if lot_scope is not None else None,
        )
        if product_ids and location_ids:
            domain = Domain(
                [
                    ("product_id", "in", product_ids.ids),
                    ("location_id", "child_of", location_ids.ids),
                ]
            )
            if lot_scope is not None:
                domain &= Domain(
                    ["|", ("lot_id", "in", lot_scope.ids), ("lot_id", "=", False)]
                )
            if extra_domain:
                domain &= Domain(extra_domain)
            needed_quants = self.env["stock.quant"]._read_group(
                domain,
                ["product_id", "location_id", "lot_id", "package_id", "owner_id"],
                ["id:recordset"],
                order="lot_id",
            )
            quant_ids = []
            for product, loc, lot, package, owner, quants in needed_quants:
                res[product.id, loc.id, lot.id, package.id, owner.id] = quants
                res.set_location_path(loc.id, loc.parent_path)
                quant_ids.extend(quants.ids)
            dbg.performance.debug(
                "quants cache: %d products, %d locations -> %d groups, %d quants",
                len(product_ids),
                len(location_ids),
                len(needed_quants),
                len(quant_ids),
            )
            self.env["stock.quant"].browse(quant_ids).fetch(
                [
                    "quantity",
                    "reserved_quantity",
                    "in_date",
                    "product_id",
                    "location_id",
                    "lot_id",
                    "package_id",
                    "owner_id",
                ]
            )
        return res

    def _get_reservation_key(self):
        self.check_singleton()
        return (self.location_id, self.lot_id, self.package_id, self.owner_id)

    def _lock_one_for_reservation(self, reserved_quantity):
        # a row this transaction already holds needs neither the lock query
        # nor a fresh read: nobody else can have written it since, and the
        # pick is the one the lock query makes -- the first lockable row in
        # recordset order -- as a row of ours is always lockable
        if not self:
            return self.env["stock.quant"]
        lockable = self
        if reserved_quantity and reserved_quantity < 0:
            reserved_rows = self.filtered(
                lambda q: q.product_uom_id.compare(q.reserved_quantity, 0) > 0
            )
            if reserved_rows:
                lockable = reserved_rows
        held = self.env.cr.cache.setdefault(LOCKED_QUANTS_CACHE_KEY, set())
        first = lockable[:1]
        if first.id in held:
            return first
        quant = lockable.try_lock_for_update(allow_referencing=True, limit=1)
        if quant:
            held.update(quant.ids)
            # the row may have changed before the lock was ours: re-read the
            # two columns alone, a bare attribute read after the invalidation
            # would prefetch every column of the row
            quant.invalidate_recordset(["quantity", "reserved_quantity"])
            quant.fetch(["quantity", "reserved_quantity"])
        return quant

    def _update_reserved_delta(self, delta):
        quant = self.sudo()._lock_one_for_reservation(delta)
        if quant:
            dbg.lifecycle.debug(
                "[quant:%s] reserved_quantity %s delta %s",
                quant.id,
                quant.reserved_quantity,
                delta,
            )
            quant.reserved_quantity = max(0, quant.reserved_quantity + delta)
        else:
            dbg.logic.debug(
                "_update_reserved_delta(%s): no lockable quant among %s",
                delta,
                dbg.rec(self),
            )
        return quant

    def _get_available_quantity(
        self,
        product_id,
        location_id,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
        allow_negative=False,
    ):
        quants = (
            self._with_block_gather_context()
            .sudo()
            ._gather(
                product_id,
                location_id,
                lot_id=lot_id,
                package_id=package_id,
                owner_id=owner_id,
                strict=strict,
            )
        )
        return self._get_available_quantity_from_quants(
            quants,
            product_id,
            lot_id=lot_id,
            strict=strict,
            allow_negative=allow_negative,
        )

    def _get_available_quantity_from_quants(
        self, quants, product_id, lot_id=None, strict=False, allow_negative=False
    ):
        quants = quants.sudo()
        ledger = self.env.context.get("reservation_ledger")
        if product_id.tracking == "none":
            available_quantity = sum(quants.mapped("quantity")) - sum(
                quants.mapped("reserved_quantity")
            )
            if ledger is not None:
                available_quantity -= sum(ledger.get_pending(quant) for quant in quants)
            if allow_negative:
                return available_quantity
            return (
                available_quantity
                if product_id.uom_id.compare(available_quantity, 0.0) >= 0.0
                else 0.0
            )
        available_quantities = dict.fromkeys(set(quants.mapped("lot_id")), 0.0)
        available_quantities[None] = 0.0
        for quant in quants:
            if not quant.lot_id and strict and lot_id:
                continue
            available_quantities[quant.lot_id or None] += (
                quant.quantity
                - quant.reserved_quantity
                - (ledger.get_pending(quant) if ledger is not None else 0.0)
            )
        if allow_negative:
            return sum(available_quantities.values())
        return sum(
            available_quantity
            for available_quantity in available_quantities.values()
            if product_id.uom_id.compare(available_quantity, 0) > 0
        )

    def _get_on_hand_shortfall(
        self, product_id, location_id, lot_id, package_id=None, owner_id=None
    ):
        quants = self.sudo()._gather(
            product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=True,
        )
        on_hand = sum(
            quant.quantity
            for quant in quants
            if quant.lot_id and quant.lot_id == lot_id
        )
        return -on_hand if product_id.uom_id.compare(on_hand, 0) < 0 else 0.0

    @api.model
    def _get_reservable_serial_quantity(
        self, product_id, requested, quantity, precision_digits
    ):
        if product_id.uom_id.compare(requested, float(int(requested))) != 0:
            return 0.0
        return float(math.floor(round(quantity, precision_digits)))

    def _get_reservation_candidates(self, quants):
        ledger = self.env.context.get("reservation_ledger")
        return [
            ReservationCandidate(
                quant,
                quant.quantity,
                quant.reserved_quantity
                + (ledger.get_pending(quant) if ledger is not None else 0.0),
                quant._get_reservation_key(),
            )
            for quant in quants
        ]

    def _get_reserve_quantity(
        self,
        product_id,
        location_id,
        quantity,
        uom_id=None,
        lot_id=None,
        package_id=None,
        owner_id=None,
        strict=False,
    ):
        self = self._with_block_gather_context(reserving=True).sudo()

        removal_strategy = self._get_removal_strategy(product_id, location_id)
        self = self.with_context(_gather_removal_strategy=removal_strategy)
        quants = self._gather(
            product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=strict,
            qty=quantity,
        )

        strategy = self._get_removal_strategy_record(removal_strategy)
        if strategy.narrows_to_packages:
            available_quantity = self._get_available_quantity(
                product_id,
                location_id,
                lot_id=lot_id,
                package_id=package_id,
                owner_id=owner_id,
                strict=strict,
            )
        else:
            available_quantity = self._get_available_quantity_from_quants(
                quants, product_id, lot_id=lot_id, strict=strict, allow_negative=False
            )

        if (
            self.env.context.get("packaging_uom_id")
            and product_id.product_tmpl_id.categ_id.packaging_reserve_method == "full"
        ):
            available_quantity = self.env.context.get(
                "packaging_uom_id"
            )._round_to_packaging_multiple(
                min(quantity, available_quantity), product_id.uom_id, "DOWN"
            )

        requested = quantity
        quantity = min(quantity, available_quantity)

        precision_digits = self.env["decimal.precision"].get_precision("Product Unit")

        if not strict and uom_id and product_id.uom_id != uom_id:
            quantity_move_uom = product_id.uom_id._get_quantity_in_unit(
                quantity, uom_id, rounding_method="DOWN"
            )
            quantity = uom_id._get_quantity_in_unit(
                quantity_move_uom, product_id.uom_id, rounding_method="HALF-UP"
            )

        whole_units = product_id.tracking == "serial"
        if whole_units:
            quantity = self._get_reservable_serial_quantity(
                product_id, requested, quantity, precision_digits
            )

        dbg.logic.debug(
            "_get_reserve_quantity product=%s location=%s requested=%s available=%s "
            "reservable=%s strict=%s over %d quants",
            product_id.id,
            location_id.id,
            requested,
            available_quantity,
            quantity,
            strict,
            len(quants),
        )
        if product_id.uom_id.compare(quantity, 0) <= 0:
            return []

        reserved = distribute_reservation(
            self._get_reservation_candidates(quants),
            quantity,
            precision_digits,
            whole_units=whole_units,
        )
        if reserved and _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(
                "reserve product=%s location=%s asked=%s -> %s",
                product_id.id,
                location_id.id,
                quantity,
                [(quant.id, qty) for quant, qty in reserved],
            )
        return reserved

    @api.model
    def _update_available_quantity(
        self,
        product_id,
        location_id,
        quantity=False,
        reserved_quantity=False,
        lot_id=None,
        package_id=None,
        owner_id=None,
        in_date=None,
    ):
        if not (quantity or reserved_quantity):
            raise ValidationError(_("Quantity or Reserved Quantity should be set."))
        dbg.lifecycle.debug(
            "_update_available_quantity product=%s location=%s lot=%s package=%s "
            "qty=%s reserved=%s",
            product_id.id,
            location_id.id,
            lot_id.id if lot_id else None,
            package_id.id if package_id else None,
            quantity,
            reserved_quantity,
        )
        location_id.with_env(self.env)._check_quantity_change_allowed(quantity)
        self = self.sudo()
        self = self.with_context(
            _gather_removal_strategy=self._get_removal_strategy(product_id, location_id)
        )
        gathered = self._gather(
            product_id,
            location_id,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
            strict=True,
        )
        quants = gathered
        if lot_id:
            if product_id.uom_id.compare(quantity, 0) > 0:
                quants = quants.filtered(lambda q: q.lot_id)
            else:
                quants = quants.filtered(
                    lambda q: product_id.uom_id.compare(q.quantity, 0) > 0 or q.lot_id,
                )

        if location_id.is_reservation_bypass_required():
            incoming_dates = []
        else:
            incoming_dates = [
                quant.in_date
                for quant in quants
                if quant.in_date and quant.product_uom_id.compare(quant.quantity, 0) > 0
            ]
        if in_date:
            incoming_dates += [in_date]
        if incoming_dates:
            in_date = min(incoming_dates)
        else:
            in_date = fields.Datetime.now()

        quant = quants._lock_one_for_reservation(reserved_quantity)

        new_quant = self.env["stock.quant"]
        if quant:
            vals = {}
            if quantity:
                vals["in_date"] = in_date
                vals["quantity"] = quant.quantity + quantity
            if reserved_quantity:
                vals["reserved_quantity"] = max(
                    0, quant.reserved_quantity + reserved_quantity
                )
            dbg.lifecycle.debug(
                "[quant:%s] updated: %s (of %d gathered)", quant.id, vals, len(gathered)
            )
            quant.write(vals)
        else:
            dbg.lifecycle.debug(
                "no quant to update among %d gathered, creating one", len(gathered)
            )
            vals = {
                "product_id": product_id.id,
                "location_id": location_id.id,
                "lot_id": lot_id and lot_id.id,
                "package_id": package_id and package_id.id,
                "owner_id": owner_id and owner_id.id,
                "in_date": in_date,
            }
            if quantity:
                vals["quantity"] = quantity
            if reserved_quantity:
                vals["reserved_quantity"] = reserved_quantity
            new_quant = self.create(vals)
        avail_quants = gathered | new_quant._filtered_not_expired()
        return (
            self._get_available_quantity_from_quants(
                avail_quants,
                product_id,
                lot_id=lot_id,
                strict=True,
                allow_negative=True,
            ),
            in_date,
        )

    @api.model
    def _update_reserved_quantity(
        self,
        product_id,
        location_id,
        quantity,
        lot_id=None,
        package_id=None,
        owner_id=None,
    ):
        self._update_available_quantity(
            product_id,
            location_id,
            reserved_quantity=quantity,
            lot_id=lot_id,
            package_id=package_id,
            owner_id=owner_id,
        )

    def _is_product_bypass_required(
        self,
        product_id=False,
        location_id=False,
        reserved_quantity=0,
        lot_id=False,
        package_id=False,
        owner_id=False,
    ):
        return False

    @dbg.timed
    def _run_maintenance_tasks(self):
        dbg.lifecycle.debug("quant maintenance start on %s", dbg.rec(self))
        self._merge_quants()
        self._sync_reserved_quantities()
        self._remove_zero_quants()
        dbg.lifecycle.debug("quant maintenance done")

    @dbg.timed
    @api.model
    def _merge_quants(self):
        params = []
        query = """WITH
                        dupes AS (
                            SELECT min(id) as to_update_quant_id,
                                (array_agg(id ORDER BY id))[2:array_length(array_agg(id), 1)] as to_delete_quant_ids,
                                GREATEST(0, SUM(reserved_quantity)) as reserved_quantity,
                                SUM(inventory_quantity) as inventory_quantity,
                                SUM(quantity) as quantity,
                                MIN(in_date) as in_date,
                                bool_or(inventory_quantity_set) as inventory_quantity_set,
                                -- Duplicates exist only because two transactions raced;
                                -- which of them carries the assignment is not meaningful,
                                -- so any deterministic survivor beats dropping it.
                                MIN(user_id) as user_id,
                                MIN(inventory_date) as inventory_date
                            FROM stock_quant
        """
        if self._ids:
            query += """
                            WHERE
                                location_id = ANY(%s)
                                AND product_id = ANY(%s)
            """
            params = [list(self.location_id.ids), list(self.product_id.ids)]
        query += """
                            GROUP BY product_id, company_id, location_id, lot_id, package_id, owner_id
                            HAVING count(id) > 1
                        ),
                        -- _up is never referenced below, but PostgreSQL always executes
                        -- data-modifying WITH clauses exactly once, so this UPDATE runs.
                        _up AS (
                            UPDATE stock_quant q
                                SET quantity = d.quantity,
                                    reserved_quantity = d.reserved_quantity,
                                    inventory_quantity = d.inventory_quantity,
                                    inventory_quantity_set = d.inventory_quantity_set,
                                    user_id = d.user_id,
                                    inventory_date = d.inventory_date,
                                    in_date = d.in_date
                            FROM dupes d
                            WHERE d.to_update_quant_id = q.id
                        )
                   DELETE FROM stock_quant WHERE id in (SELECT unnest(to_delete_quant_ids) from dupes)
        """
        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(query, params)
                dbg.lifecycle.debug(
                    "_merge_quants: %s rows deleted", self.env.cr.rowcount
                )
                self.env.invalidate_all()
        except Error as e:
            _logger.warning(
                "an error occurred while merging quants: %s (%s)",
                e,
                type(e).__name__,
            )

    @dbg.timed
    @api.model
    def _sync_reserved_quantities(self, products=None, locations=None):
        quant_domain = Domain("reserved_quantity", "!=", 0)
        move_line_domain = Domain(
            [
                (
                    "state",
                    "in",
                    ["assigned", "partially_available", "waiting", "confirmed"],
                ),
                ("quantity_product_uom", "!=", 0),
                ("product_id.is_storable", "=", True),
            ],
        )
        if self._ids:
            quants = self.exists()
            products = quants.product_id
            locations = quants.location_id
        scope_domain = Domain.TRUE
        if products is not None:
            scope_domain &= Domain("product_id", "in", products.ids)
        if locations is not None:
            scope_domain &= Domain("location_id", "in", locations.ids)
        quant_domain &= scope_domain
        move_line_domain &= scope_domain
        reserved_quants = self.env["stock.quant"]._read_group(
            quant_domain,
            ["product_id", "location_id", "lot_id", "package_id", "owner_id"],
            ["reserved_quantity:sum", "id:recordset"],
        )
        reserved_move_lines = self.env["stock.move.line"]._read_group(
            move_line_domain,
            ["product_id", "location_id", "lot_id", "package_id", "owner_id"],
            ["quantity_product_uom:sum"],
        )
        reserved_move_lines = {
            (product, location, lot, package, owner): reserved_quantity
            for product, location, lot, package, owner, reserved_quantity in reserved_move_lines
        }
        dbg.performance.debug(
            "_sync_reserved_quantities: %d reserved quant groups, %d move line groups",
            len(reserved_quants),
            len(reserved_move_lines),
        )
        for (
            product,
            location,
            lot,
            package,
            owner,
            reserved_quantity,
            quants,
        ) in reserved_quants:
            ml_reserved_qty = reserved_move_lines.get(
                (product, location, lot, package, owner), 0
            )
            if location.is_reservation_bypass_required():
                dbg.logic.debug(
                    "sync: bypass location %s, releasing %s on %s",
                    location.id,
                    reserved_quantity,
                    dbg.rec(quants),
                )
                quants._update_reserved_delta(-reserved_quantity)
            elif product.uom_id.compare(reserved_quantity, ml_reserved_qty) != 0:
                dbg.logic.debug(
                    "sync: product %s location %s quant reserved %s vs lines %s on %s",
                    product.id,
                    location.id,
                    reserved_quantity,
                    ml_reserved_qty,
                    dbg.rec(quants),
                )
                quants._update_reserved_delta(ml_reserved_qty - reserved_quantity)
            if ml_reserved_qty:
                del reserved_move_lines[(product, location, lot, package, owner)]

        for (
            product,
            location,
            lot,
            package,
            owner,
        ), reserved_quantity in reserved_move_lines.items():
            if location.is_reservation_bypass_required() or self.env[
                "stock.quant"
            ]._is_product_bypass_required(
                product, location, reserved_quantity, lot, package, owner
            ):
                continue
            dbg.logic.debug(
                "sync: lines reserve %s of product %s at %s with no quant reservation",
                reserved_quantity,
                product.id,
                location.id,
            )
            self.env["stock.quant"]._update_reserved_quantity(
                product,
                location,
                reserved_quantity,
                lot_id=lot,
                package_id=package,
                owner_id=owner,
            )

    @dbg.timed
    @api.model
    def _remove_zero_quants(self, products=None, locations=None):
        self.env["stock.quant"].flush_model(
            ["quantity", "reserved_quantity", "inventory_quantity", "user_id"]
        )
        precision_digits = max(
            6, self.env.ref("uom.decimal_product_uom").sudo().digits * 2
        )
        epsilon = Decimal(5) * Decimal(10) ** -(precision_digits + 1)
        query = SQL(
            """SELECT id FROM stock_quant
                -- `round(x, n) = 0` is `|x| < 0.5 * 10 ** -n`, spelled as a range so
                -- an index on the column stays usable. The columns are `numeric` and
                -- the ORM rounds on write, so nothing but a raw writer can land here.
                WHERE quantity > %(low)s AND quantity < %(high)s
                  AND reserved_quantity > %(low)s AND reserved_quantity < %(high)s
                  AND (inventory_quantity IS NULL
                       OR (inventory_quantity > %(low)s
                           AND inventory_quantity < %(high)s))
                  AND user_id IS NULL""",
            low=-epsilon,
            high=epsilon,
        )
        if self._ids:
            quants = self.exists()
            products = quants.product_id
            locations = quants.location_id
        if locations is not None:
            query = SQL("%s AND location_id = ANY(%s)", query, list(locations.ids))
        if products is not None:
            query = SQL("%s AND product_id = ANY(%s)", query, list(products.ids))
        quants = self.env["stock.quant"].browse(
            row[0] for row in self.env.execute_query(query)
        )
        dbg.lifecycle.debug("_remove_zero_quants: %s", dbg.rec(quants))
        quants.sudo().unlink()
