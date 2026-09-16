from datetime import timedelta
from typing import Literal, Self

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.numbers import RoundingMethod, float_repr
from odoo.tools import float_compare, float_is_zero, float_round

#: Decimals used to render `relative_factor` for humans -- enough for every
#: factor the module ships (the tightest is 0.0163871, in³ per litre). It is a
#: display concern only: the column itself is an unlimited NUMERIC.
_RELATIVE_FACTOR_DIGITS = 7


class UomUom(models.Model):
    _name = "uom.uom"
    _description = "Product Unit of Measure"
    _parent_name = "relative_uom_id"
    _parent_store = True
    # `relative_uom_id` here made every search LEFT JOIN uom_uom to itself and
    # order by the *parent's* sequence, which is 100 or 1000 for most parents.
    # `parent_path` groups a family in one indexed column, with no join.
    _order = "sequence, parent_path, id"

    name = fields.Char(
        string="Unit Name",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        compute="_compute_sequence",
        precompute=True,
        store=True,
        readonly=False,
    )
    relative_factor = fields.Float(
        string="Contains",
        digits=0,  # falsy digits force NUMERIC with unlimited precision
        default=1.0,
        required=True,
        help="How much bigger or smaller this unit is compared to the reference UoM for this unit",
    )
    rounding = fields.Float(
        string="Rounding Precision",
        compute="_compute_rounding",
    )
    active = fields.Boolean(
        default=True,
        help="Uncheck the active field to disable a unit of measure without deleting it.",
    )
    relative_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Reference Unit",
        index="btree_not_null",
        ondelete="cascade",
    )
    factor = fields.Float(
        string="Absolute Quantity",
        digits=0,
        compute="_compute_factor",
        recursive=True,
        store=True,
    )
    reference_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Dimension",
        compute="_compute_reference_uom_id",
        recursive=True,
        store=True,
        index="btree_not_null",
        help="The root unit this one is ultimately defined against."
        " Two units are convertible if and only if they share it.",
    )
    parent_path = fields.Char(index=True)

    _factor_gt_zero = models.Constraint(
        "CHECK (relative_factor > 0)",
        "The conversion ratio for a unit of measure must be strictly positive!",
    )

    # === COMPUTE METHODS === #

    @api.depends("relative_factor")
    def _compute_sequence(self):
        """Seed a sequence from the magnitude of the unit, once, at creation.

        The guard tests `uom.id` alone. It used to also test `uom.sequence`,
        which reads as "fill it in if empty" but cannot mean that: `sequence`
        is an Integer, so an unset column and a deliberate 0 both arrive here
        as 0. Dragging a unit to the top of the list (the handle widget writes
        sequence 0) was therefore undone by the next `relative_factor` edit,
        which recomputed it back to a magnitude-derived value.

        The floor of 1 exists for the same reason: `relative_factor < 0.01`
        produced sequence 0 on its own, so a computed value was indistinguishable
        from a hand-placed first row.
        """
        for uom in self:
            if uom.id:
                # Existing records keep whatever ordering they were given.
                continue
            uom.sequence = max(1, min(int(uom.relative_factor * 100.0), 1000))

    def _compute_rounding(self):
        """All Units of Measure share the same rounding precision defined in 'Product Unit'.
        Set in a compute to ensure compatibility with previous calls to `uom.rounding`.

        There is deliberately no `@api.depends`: the value follows a
        `decimal.precision` row, not a field of `self`, so the ORM has nothing to
        watch. `decimal.precision.write` is extended (see `decimal_precision.py`)
        to invalidate this field, which is what keeps a cached `rounding` from
        disagreeing with `_precision_digits()` inside a single transaction.
        """
        self.rounding = 10 ** -self._precision_digits()

    @api.depends("relative_factor", "relative_uom_id", "relative_uom_id.factor")
    def _compute_factor(self):
        for uom in self:
            if uom.relative_uom_id:
                uom.factor = uom.relative_factor * uom.relative_uom_id.factor
            else:
                uom.factor = uom.relative_factor

    @api.depends("relative_uom_id", "relative_uom_id.reference_uom_id")
    def _compute_reference_uom_id(self):
        """The root of the chain, materialised as a column.

        This is the dimension: 19.0 replaced `uom.category` with the
        reference-unit tree but left the root implicit, so every consumer
        re-derived it -- `_has_common_reference` compared `parent_path`
        prefixes and the autocomplete widget did `parent_path.split("/")[0]`
        to build a `=like` domain. Both are an equality test now, and
        "compatible with X" is expressible as a plain domain for the first
        time, which is what `parent_path` never gave callers.

        `pos_blackbox_be` still derives the root from `parent_path`
        client-side; that field stays, so it is unaffected.

        Deliberately not `precompute`: a root unit is its own reference, and
        the id it needs does not exist until after the INSERT.
        """
        for uom in self:
            uom.reference_uom_id = uom.relative_uom_id.reference_uom_id or uom

    # === ONCHANGE METHODS === #

    @api.onchange("relative_factor", "relative_uom_id")
    def _onchange_critical_fields(self):
        if self._filter_protected_uoms() and self.create_date < (
            fields.Datetime.now() - timedelta(days=1)
        ):
            return {
                "warning": {
                    "title": _("Warning for %s", self.name),
                    "message": _(
                        "Some critical fields have been modified on %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As units of measure impact the whole system, this may cause critical issues.\n"
                        "Therefore, changing core units of measure in a running database is not recommended.",
                        self.name,
                    ),
                }
            }
        return None

    # === CONSTRAINT METHODS === #

    @api.constrains("relative_factor", "relative_uom_id")
    def _check_factor(self):
        for uom in self:
            if (
                not uom.relative_uom_id
                and float_compare(uom.relative_factor, 1.0, precision_digits=12) != 0
            ):
                raise UserError(
                    _(
                        "The unit of measure %s has a conversion ratio but no reference unit."
                        " Either set a reference unit or keep a ratio of 1.",
                        uom.display_name,
                    )
                )

    # === CRUD METHODS === #

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        """Veto a delete that would take units with it that the caller never named.

        `relative_uom_id` is `ondelete="cascade"`, so Postgres removes every
        descendant of `self` in the same statement -- without any of them ever
        passing through `unlink()`. Vetting only `self` therefore left two holes:

        - Deleting `Hours` (deliberately unprotected, see
          `_unprotected_uom_xml_ids`) silently deleted `Days` and `Minutes`,
          which *are* protected master data, and left their `ir.model.data`
          rows behind: `env.ref("uom.product_uom_day")` then raised for every
          module built on it.
        - Deleting any user-made reference unit silently deleted the whole
          family defined against it.

        Both are checked here, on `self` plus its descendants. Deleting a
        subtree explicitly (parent and children in the same recordset) stays
        allowed -- the intent is unambiguous then.
        """
        descendants = self._descendant_uoms()
        locked_uoms = (self | descendants)._filter_protected_uoms()
        if locked_uoms:
            raise UserError(
                _(
                    "The following units of measure are used by the system and cannot be deleted: %s\nYou can archive them instead.",
                    ", ".join(locked_uoms.mapped("name")),
                )
            )
        if descendants:
            raise UserError(
                _(
                    "%(unit)s is the reference unit of %(dependent_units)s."
                    " Deleting it would delete those too. Delete them first, or"
                    " give them another reference unit.",
                    unit=", ".join(self.mapped("name")),
                    dependent_units=", ".join(descendants.mapped("name")),
                )
            )

    # === BUSINESS METHODS === #

    def _precision_digits(self) -> int:
        """Number of decimals every unit is rounded at.

        Single accessor for the 'Product Unit' precision, so `rounding`,
        `round`, `compare` and `is_zero` cannot drift apart the way three
        independent `get_precision` calls could. Cheap to call in a loop:
        `get_precision` is ormcached on the "stable" cache.
        """
        return self.env["decimal.precision"].get_precision("Product Unit")

    def round(self, value: float, rounding_method: RoundingMethod = "HALF-UP") -> float:
        """Round the value using the 'Product Unit' precision

        Callable on an empty recordset; see :meth:`_check_at_most_one`. Like
        `compare` and `is_zero` it never reads `self`, so it accepts exactly
        the same receivers they do -- it was the last of the three still
        raising on an unset unit.

        :param value: value to round
        :return: ``value`` rounded to the 'Product Unit' precision
        :rtype: float
        """
        self._check_at_most_one()
        return float_round(
            value,
            precision_digits=self._precision_digits(),
            rounding_method=rounding_method,
        )

    def _check_at_most_one(self) -> None:
        """Reject a multi-record set, accept an empty one.

        `compare` and `is_zero` round at the 'Product Unit' decimal precision and
        never read `self`, so their answer cannot depend on *which* unit is held --
        yet `check_singleton()` made them raise on an **empty** one. Callers legitimately
        compare quantities on records whose unit is not resolved yet: a brand-new
        `stock.warehouse.orderpoint` built from a list view's defaults has no product,
        hence no `product_uom_id`, while every quantity on it is still 0.0. Demanding
        a unit there turned a well-defined comparison into a crash, which is why the
        raw `<` these methods replace kept surviving in the codebase.

        More than one unit stays a caller error -- that really is ambiguous.
        """
        if len(self) > 1:
            self.check_singleton()

    def compare(self, value1: float, value2: float) -> Literal[-1, 0, 1]:
        """Compare two measures after rounding them with the 'Product Unit' precision

        Callable on an empty recordset; see :meth:`_check_at_most_one`.

        :param value1: origin value to compare
        :param value2: value to compare to
        :return: -1, 0 or 1, if ``value1`` is lower than, equal to, or greater than ``value2``.
        """
        self._check_at_most_one()
        return float_compare(value1, value2, precision_digits=self._precision_digits())

    def is_zero(self, value: float) -> bool:
        """Check if the value is zero after rounding with the 'Product Unit' precision

        Callable on an empty recordset; see :meth:`_check_at_most_one`.

        :param value: value to check
        :return: whether ``value`` rounds to zero at the 'Product Unit' precision
        :rtype: bool
        """
        self._check_at_most_one()
        return float_is_zero(value, precision_digits=self._precision_digits())

    @api.depends("name", "relative_factor", "relative_uom_id", "relative_uom_id.name")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for uom in self:
            if uom.env.context.get("formatted_display_name") and uom.relative_uom_id:
                # `float_repr`, not `str`: `relative_factor` is stored as an
                # unlimited NUMERIC, so interpolating the raw float printed
                # "Minutes --0.016666666666666666 Hours--" in every dropdown
                # that asks for a formatted name.
                factor = (
                    float_repr(uom.relative_factor, _RELATIVE_FACTOR_DIGITS)
                    .rstrip("0")
                    .rstrip(".")
                )
                uom.display_name = (
                    f"{uom.name}\t--{factor or '0'} {uom.relative_uom_id.name}--"
                )

    def _get_quantity_in_unit(
        self,
        qty: float,
        to_unit: Self,
        round: bool = True,
        rounding_method: RoundingMethod = "UP",
        raise_if_failure: bool = True,
    ) -> float:
        """Convert the given quantity from the current UoM `self` into a given one

        :param qty: the quantity to convert
        :param to_unit: the destination UomUom record (uom.uom)
        :param raise_if_failure: behavior when the conversion is not possible
            (`self` and `to_unit` have no common reference unit):
            - if true, raise a UserError,
            - otherwise, return the initial quantity unconverted

        Call-sites that must degrade instead of raising use the named
        wrappers below (`_get_quantity_report` / `_get_quantity_estimate`
        / `_get_quantity_reconcile`) — see the comment block above them
        for the decision rule.
        """
        if not self or not qty:
            # `qty or 0.0`, not `qty`: the annotation promises a float, and the
            # falsy inputs that reach here are `False` (an unset Float read off
            # a half-filled record) and `None`, both of which were handed back
            # unchanged.
            return qty or 0.0
        self.check_singleton()

        if self == to_unit:
            amount = qty
        else:
            if to_unit and not self._has_common_reference(to_unit):
                if raise_if_failure:
                    raise UserError(
                        _(
                            "The unit of measure %(unit)s cannot be converted into %(other_unit)s"
                            " because they do not share a common reference unit.",
                            unit=self.name,
                            other_unit=to_unit.name,
                        )
                    )
                return qty
            amount = qty * self.factor
            if to_unit:
                amount /= to_unit.factor

        if to_unit and round:
            amount = float_round(
                amount,
                precision_rounding=to_unit.rounding,
                rounding_method=rounding_method,
            )

        return amount

    # --- Degrade-on-failure wrappers ------------------------------------
    # `_get_quantity_in_unit` raises when the units share no common reference.
    # Call-sites that must degrade instead (return the quantity unconverted,
    # visibly wrong but non-blocking) use one of the named wrappers below so
    # the intent stays greppable per bucket. Pick by what the value feeds:
    # - _get_quantity_report: a screen, PDF or aggregate display.
    # - _get_quantity_estimate: a forecast/planning/pricing estimate
    #   that guides but does not size a record.
    # - _get_quantity_reconcile: a stored reconciliation compute
    #   (qty_transferred/qty_invoiced family) matching moves or invoice
    #   lines back to order lines. These are stored, so the ORM replays them
    #   over every row when a column is created or a dependency changes:
    #   raising there lets one legacy row abort an unrelated flush. The
    #   fail-closed requirement therefore lives at the invoicing boundary,
    #   not in the compute — `_assert_transferred_uom_convertible` (re-runs
    #   the compute under the `uom_reconcile_strict` context) and
    #   `_assert_invoiced_uom_convertible` (checks the conversions without
    #   recomputing), both in `base_order`.
    # Anything that creates or sizes a real record (moves, MOs, order lines,
    # valuation/COGS) stays on the strict base method. The opt-out is forced:
    # a caller-passed `raise_if_failure` is discarded.

    def _get_quantity_lenient(self, qty: float, to_unit: Self, **kwargs) -> float:
        """Shared body of the degrade wrappers; call those, not this."""
        kwargs.pop("raise_if_failure", None)
        return self._get_quantity_in_unit(
            qty, to_unit, raise_if_failure=False, **kwargs
        )

    def _get_quantity_report(self, qty: float, to_unit: Self, **kwargs) -> float:
        """Convert for a display/report value; degrades on incompatible units."""
        return self._get_quantity_lenient(qty, to_unit, **kwargs)

    def _get_quantity_estimate(self, qty: float, to_unit: Self, **kwargs) -> float:
        """Convert for a planning/pricing estimate; degrades on incompatible units."""
        return self._get_quantity_lenient(qty, to_unit, **kwargs)

    def _get_quantity_reconcile(self, qty: float, to_unit: Self, **kwargs) -> float:
        """Convert for a stored reconciliation compute; degrades on incompatible units.

        Escalates to strict (raises) when the environment flags a posting
        boundary via the `uom_reconcile_strict` context key. This keeps the
        stored `qty_transferred`/`qty_transferred_at_date` computes lenient
        while an order is browsed (never blocking on legacy incompatible-UoM
        data), yet fails loud when that quantity is about to size an
        invoice/bill line or an accrual amount — so nothing financial is ever
        posted on a silently unconverted quantity. See
        `order.line.fields.mixin._assert_transferred_uom_convertible`.
        """
        if self.env.context.get("uom_reconcile_strict"):
            kwargs.pop("raise_if_failure", None)
            return self._get_quantity_in_unit(
                qty, to_unit, raise_if_failure=True, **kwargs
            )
        return self._get_quantity_lenient(qty, to_unit, **kwargs)

    def _conversion_rounding(self, to_unit: Self) -> float:
        """The rounding step that preserves this unit's resolution in `to_unit`."""
        self._check_at_most_one()
        if (
            not self
            or not to_unit
            or self == to_unit
            or not self.factor
            or not to_unit.factor
        ):
            return to_unit.rounding if to_unit else self.rounding
        return to_unit.rounding * min(1.0, self.factor / to_unit.factor)

    def _get_quantity_stored(
        self, qty: float, to_unit: Self, rounding_method: RoundingMethod = "HALF-UP"
    ) -> float:
        """Convert for a value stored or consumed as the authoritative quantity."""
        if not self or not qty or not to_unit or self == to_unit:
            return self._get_quantity_in_unit(
                qty, to_unit, rounding_method=rounding_method
            )
        self.check_singleton()
        amount = self._get_quantity_in_unit(qty, to_unit, round=False)
        return float_round(
            amount,
            precision_rounding=self._conversion_rounding(to_unit),
            rounding_method=rounding_method,
        )

    def _aggregate_rounding(self) -> float:
        """The step of this dimension's reference unit, expressed in this unit."""
        self.check_singleton()
        return self.rounding / max(1.0, self.factor)

    def _is_zero_aggregate(self, qty: float) -> bool:
        """Is `qty`, a total with no single source unit, zero at any resolution?"""
        self._check_at_most_one()
        if not self:
            return float_is_zero(qty, precision_digits=self._precision_digits())
        return float_is_zero(qty, precision_rounding=self._aggregate_rounding())

    def _round_aggregate(self, qty: float) -> float:
        """Round a total that has no single source unit."""
        self._check_at_most_one()
        if not self:
            return float_round(qty, precision_digits=self._precision_digits())
        return float_round(qty, precision_rounding=self._aggregate_rounding())

    def _compare_aggregate(self, qty1: float, qty2: float) -> int:
        """Compare two totals that have no single source unit."""
        self._check_at_most_one()
        if not self:
            return float_compare(qty1, qty2, precision_digits=self._precision_digits())
        return float_compare(qty1, qty2, precision_rounding=self._aggregate_rounding())

    def _is_zero_stored(self, qty: float, to_unit: Self) -> bool:
        """Is `qty`, already converted into `to_unit`, zero at the stored resolution?"""
        self._check_at_most_one()
        if not self:
            return to_unit.is_zero(qty)
        return float_is_zero(qty, precision_rounding=self._conversion_rounding(to_unit))

    def _round_to_packaging_multiple(
        self, product_qty: float, uom: Self, rounding_method: RoundingMethod = "HALF-UP"
    ) -> float:
        """Round `product_qty` (expressed in `uom`) to a whole multiple of the
        packaging `self`, according to `rounding_method` ("UP", "HALF-UP" or "DOWN").

        Named `_check_qty` until now, which described neither the argument nor
        the return: it checks nothing and answers with a quantity. One
        production call site (`stock.quant._get_available_quantity`, the
        "reserve whole packages only" branch).
        """
        self.check_singleton()
        if self == uom:
            return product_qty
        # One package expressed in `uom`, unrounded: rounding it first would
        # distort the multiples (e.g. a Unit is 1/12 Dozen, not 0.08).
        packaging_qty = self._get_quantity_in_unit(1, uom, round=False)
        # We do not use the modulo operator to check if qty is a multiple of q. Indeed the quantity
        # per package might be a float, leading to incorrect results. For example:
        # 8 % 1.6 = 1.5999999999999996
        # 5.4 % 1.8 = 2.220446049250313e-16
        if product_qty and packaging_qty:
            product_qty = (
                float_round(
                    product_qty / packaging_qty,
                    precision_rounding=1.0,
                    rounding_method=rounding_method,
                )
                * packaging_qty
            )
            # The whole-package count is already fixed; this only strips float
            # artefacts (e.g. 144 * 1/12 = 12.000000000000002).
            product_qty = float_round(
                product_qty, precision_rounding=uom.rounding, rounding_method="HALF-UP"
            )
        return product_qty

    def _get_price_in_unit(
        self, price: float, to_unit: Self, raise_if_failure: bool = True
    ) -> float:
        """Convert a price per unit of `self` into a price per unit of `to_unit`.

        Strict by default, exactly like `_get_quantity_in_unit`: scaling by the
        ratio of two factors is only meaningful when both units measure the
        same thing. Without the check a price of 100 per kg asked for "in
        Units" came back as 0.1 -- a plausible-looking number that is off by
        the raw factor ratio, with nothing to distinguish it from a real one.

        Call-sites that must degrade instead of raising use the named wrappers
        below (`_get_price_report` / `_get_price_estimate`) -- see the
        comment block above them for the decision rule.

        Degenerate recordsets are handled exactly as in `_get_quantity_in_unit`: an
        unset unit on either side returns the price untouched instead of
        raising. The two were asymmetric -- `_compute_price` `check_singleton()`d
        first, so a price read off a record whose unit is not resolved yet blew
        up with `ValueError` where the quantity path returned quietly.
        """
        if not self or not price or not to_unit or self == to_unit:
            return price
        self.check_singleton()
        if not self._has_common_reference(to_unit):
            if raise_if_failure:
                raise UserError(
                    _(
                        "A price per %(unit)s cannot be converted into a price per"
                        " %(other_unit)s because they do not share a common"
                        " reference unit.",
                        unit=self.name,
                        other_unit=to_unit.name,
                    )
                )
            return price
        return price * to_unit.factor / self.factor

    # --- Degrade-on-failure wrappers ------------------------------------
    # Same rule as the quantity family above: anything that prices a real
    # record (an order line, a valuation, a bill) stays on the strict base
    # method. Pick a wrapper only when the value feeds:
    # - _get_price_report: a screen, PDF or aggregate display.
    # - _get_price_estimate: a forecast/planning estimate that guides but
    #   does not size a record.
    # The vendor unit on `product.supplierinfo` is deliberately allowed to be
    # cross-category, so the seller-price call-sites are the ones that
    # legitimately need to degrade rather than raise.
    # Do not read that as "something else already filtered those sellers out".
    # `product.product._get_filtered_sellers` does drop cross-category sellers,
    # but only when it is given both a `uom_id` and a non-zero `quantity`; with
    # the default `quantity=0.0` the check never runs. Every use site that feeds
    # a seller unit into a *strict* conversion has to filter for itself -- see
    # `account.move.line._compute_product_uom_id`, which did not, and blocked
    # the vendor bill with a UserError.
    # The opt-out is forced: a caller-passed `raise_if_failure` is discarded.

    def _get_price_lenient(self, price: float, to_unit: Self, **kwargs) -> float:
        """Shared body of the degrade wrappers; call those, not this."""
        kwargs.pop("raise_if_failure", None)
        return self._get_price_in_unit(price, to_unit, raise_if_failure=False, **kwargs)

    def _get_price_report(self, price: float, to_unit: Self, **kwargs) -> float:
        """Convert a price for a display/report value; degrades on incompatible units."""
        return self._get_price_lenient(price, to_unit, **kwargs)

    def _get_price_estimate(self, price: float, to_unit: Self, **kwargs) -> float:
        """Convert a price for a planning estimate; degrades on incompatible units."""
        return self._get_price_lenient(price, to_unit, **kwargs)

    def _unprotected_uom_xml_ids(self):
        """Return a list of UoM XML IDs that are not protected by default.
        Note: Some of these may be protected via overrides in other modules.
        """
        return [
            "product_uom_hour",
            "product_uom_dozen",
            "product_uom_pack_6",
        ]

    def _filter_protected_uoms(self):
        """Return the subset of `self` that is protected master data.

        Any module's master data counts, not just this one's. The query used to
        be pinned to `module = "uom"`, but sixteen modules ship `uom.uom`
        records -- `l10n_mx`, `l10n_in`, `l10n_cl`, `hr_timesheet`,
        `hr_expense`, `point_of_sale` and several enterprise `l10n_*`. None of
        them were protected, so a leaf unit from any of them deleted cleanly
        and took its xml id with it: `env.ref("uom.product_uom_mw")` then
        raised for every module built on it. The descendant guard in
        `_unlink_except_master_data` blocked the cascade, never the direct
        delete.
        """
        linked_model_data = (
            self.env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("model", "=", self._name),
                    ("res_id", "in", self.ids),
                    ("name", "not in", self._unprotected_uom_xml_ids()),
                ]
            )
        )
        return self.browse(set(linked_model_data.mapped("res_id")))

    def _descendant_uoms(self) -> Self:
        """Every unit transitively defined against `self`, `self` excluded.

        `active_test=False` is not optional: half the shipped hierarchy is
        archived (cm, Dozens, the imperial units...), and an archived child is
        cascade-deleted exactly like an active one.
        """
        if not self:
            return self
        return (
            self.with_context(active_test=False).search([("id", "child_of", self.ids)])
            - self
        )

    def _get_reference_uom(self) -> Self:
        """Return the root unit `self` is (transitively) defined against."""
        self.check_singleton()
        # One indexed column read, at any depth. This walked
        # `relative_uom_id` once per level (6 queries for a Mile), then read it
        # off `parent_path`; `reference_uom_id` now stores it outright.
        return self.reference_uom_id or self

    def _has_common_reference(self, other_uom: Self) -> bool:
        """Check if `self` and `other_uom` have a common reference unit

        An unset unit on either side is `False`: it shares a reference with
        nothing, since there is no reference to share. It is not a caller error
        -- the ~30 call sites reach `product_uom_id`, `uom_id` or a
        `seller.product_uom_id` that is legitimately empty on a half-filled
        record, and each of them had to pre-guard the operands to avoid a bare
        `ValueError`. More than one unit stays a caller error: that really is
        ambiguous. Same rule as :meth:`_check_at_most_one`.
        """
        self._check_at_most_one()
        other_uom._check_at_most_one()
        if not self or not other_uom:
            return False
        return self._get_reference_uom() == other_uom._get_reference_uom()
