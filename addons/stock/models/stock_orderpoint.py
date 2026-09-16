import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import DOMAIN_PREDICATES, TransactionMemo, frozendict

from ..tools import debug_log as dbg

# the fields that decide which orderpoints a move's product and warehouses
# reach; a write to any of them discards the transaction's memo
ORDERPOINT_SCOPE_FIELDS = ("product_id", "warehouse_id", "active", "company_id")
ORDERPOINTS_BY_SCOPE = TransactionMemo(
    "stock.warehouse.orderpoint.by_scope",
    invalidated_by={"stock.warehouse.orderpoint": ORDERPOINT_SCOPE_FIELDS},
)

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _name = "stock.warehouse.orderpoint"
    _description = "Minimum Inventory Rule"
    _check_company_auto = True
    _order = "location_id,company_id,id"

    _LEAD_TIME_SAMPLE_SIZE = 20
    _LEAD_TIME_LOOKBACK_DAYS = 730
    _PROCUREMENT_RETRIES = 5

    name = fields.Char(
        default=lambda self: self.env["ir.sequence"].next_by_code("stock.orderpoint"),
        copy=False,
        readonly=True,
        required=True,
    )
    trigger = fields.Selection(
        selection=[("auto", "Auto"), ("manual", "Manual")],
        default="auto",
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to False, it will allow you to hide the orderpoint without removing it.",
    )
    snoozed_until = fields.Date(
        string="Snoozed",
        help="Hidden from the replenishment report until this date has passed.",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        compute="_compute_location_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        related="product_id.product_tmpl_id",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        index=True,
        required=True,
        domain="[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else"
        " [('id', '=', context.get('default_product_id', False))] if context.get('default_product_id') else"
        " [('is_storable', '=', True)]",
        ondelete="cascade",
        check_company=True,
    )
    product_category_id = fields.Many2one(
        comodel_name="product.category",
        related="product_id.categ_id",
        string="Product Category",
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        string="Unit",
    )
    product_uom_name = fields.Char(
        related="product_uom_id.display_name",
        string="Product unit of measure label",
        readonly=True,
    )
    product_min_qty = fields.Float(
        string="Min Quantity",
        digits="Product Unit",
        default=0.0,
        required=True,
        help="The minimum Stock level that will trigger a replenishment.",
    )
    product_max_qty = fields.Float(
        string="Max Quantity",
        digits="Product Unit",
        compute="_compute_product_max_qty",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="Stock level to reach when replenishing.",
    )
    allowed_replenishment_uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        compute="_compute_allowed_replenishment_uom_ids",
    )
    replenishment_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Multiple",
        domain="[('id', 'in', allowed_replenishment_uom_ids)]",
        help="The procurement quantity will be rounded up to a multiple of this unit/packaging. If it is not set, it is not rounded.",
    )
    replenishment_uom_id_placeholder = fields.Char(
        compute="_compute_replenishment_uom_id_placeholder"
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        required=True,
    )
    allowed_location_ids = fields.Many2many(
        comodel_name="stock.location",
        compute="_compute_allowed_location_ids",
    )

    rule_ids = fields.Many2many(
        comodel_name="stock.rule",
        string="Rules used",
        compute="_compute_rule_ids",
    )
    lead_horizon_date = fields.Date(compute="_compute_lead_time")
    lead_days = fields.Float(compute="_compute_lead_time")
    route_id = fields.Many2one(
        comodel_name="stock.route",
        inverse="_inverse_route_id",
        domain="['|', ('product_selectable', '=', True), ('rule_ids.action', 'in', ['buy', 'manufacture'])]",
    )
    route_id_placeholder = fields.Char(compute="_compute_route_id_placeholder")
    effective_route_id = fields.Many2one(
        comodel_name="stock.route",
        compute="_compute_effective_route_id",
        search="_search_effective_route_id",
        store=False,
        help="Either the route set directly or the one computed to be used by this replenishment",
    )
    qty_on_hand = fields.Float(
        string="On Hand",
        digits="Product Unit",
        compute="_compute_qty",
        readonly=True,
    )
    qty_forecast = fields.Float(
        string="Forecast",
        digits="Product Unit",
        compute="_compute_qty",
        readonly=True,
    )
    qty_to_order = fields.Float(
        string="To Order",
        digits="Product Unit",
        compute="_compute_qty_to_order",
        inverse="_inverse_qty_to_order",
        search="_search_qty_to_order",
    )
    qty_to_order_computed = fields.Float(
        string="To Order Computed",
        digits="Product Unit",
        compute="_compute_qty_to_order_computed",
        store=True,
    )
    qty_to_order_manual = fields.Float(
        string="To Order Manual",
        digits="Product Unit",
    )
    qty_to_order_manual_set = fields.Boolean(
        string="Quantity Overridden",
        default=False,
        help="Technical: the user entered a quantity to order on this "
        "manually-triggered orderpoint that differs from the computed suggestion, "
        "and `qty_to_order_manual` holds it. A Float cannot tell an explicit 0 from "
        "no value at all, so whether an override exists is recorded separately from "
        "what it is -- which is why an override of 0 needs no special case.",
    )
    is_autogenerated = fields.Boolean(
        string="Autogenerated",
        default=False,
        help="Technical: set on orderpoints created automatically by the "
        "replenishment report for a projected shortage. Only these are "
        "auto-vacuumed once their shortage is resolved. Rows created before "
        "this field existed conservatively keep it unset and are therefore "
        "no longer auto-vacuumed.",
    )

    days_to_order = fields.Float(
        compute="_compute_days_to_order",
        help="Numbers of days  in advance that replenishments demands are created.",
    )

    unwanted_replenish = fields.Boolean(compute="_compute_unwanted_replenish")
    show_supply_warning = fields.Boolean(compute="_compute_show_supply_warning")
    deadline_date = fields.Date(
        string="Deadline",
        compute="_compute_deadline_date",
        store=True,
        readonly=True,
        help="Date before which you should order to avoid falling below the minimum. If you "
        "have nothing to order while a deadline is found, it may be because a future "
        "arrival is expected after the minimum quantity is reached (potential stockout). "
        "Check the Forecast Report.",
    )

    actual_lead_time_avg = fields.Float(
        string="Avg Lead Time (days)",
        digits=(10, 2),
        compute="_compute_lead_time_stats",
        store=True,
        help="Average actual procurement lead time in days, measured from "
        "completed incoming transfers for this product and warehouse.",
    )
    actual_lead_time_stddev = fields.Float(
        string="Lead Time Std Dev (days)",
        digits=(10, 2),
        compute="_compute_lead_time_stats",
        store=True,
        help="Standard deviation of actual procurement lead times. "
        "Higher values indicate less predictable suppliers.",
    )
    lead_time_sample_count = fields.Integer(
        string="Lead Time Samples",
        compute="_compute_lead_time_stats",
        store=True,
        help="Number of completed incoming transfers used to compute lead time statistics.",
    )

    _product_location_check = models.Constraint(
        "unique (product_id, location_id, company_id)",
        "A replenishment rule already exists for this product on this location.",
    )

    @api.constrains("product_min_qty", "product_max_qty")
    def _check_min_max_qty(self):
        if any(
            orderpoint.product_uom_id.compare(
                orderpoint.product_min_qty, orderpoint.product_max_qty
            )
            > 0
            for orderpoint in self
        ):
            raise ValidationError(
                _(
                    "The minimum quantity must be less than or equal to the maximum quantity.",
                ),
            )

    @api.model
    def _update_vals_manual_qty_override(self, vals):
        if "qty_to_order_manual" in vals and "qty_to_order_manual_set" not in vals:
            vals = dict(vals, qty_to_order_manual_set=True)
        return vals

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "orderpoint.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        vals_list = [self._update_vals_manual_qty_override(vals) for vals in vals_list]
        default_trigger = None
        if any(vals.get("snoozed_until") for vals in vals_list):
            default_trigger = self.default_get(["trigger"])["trigger"]
        if any(
            vals.get("snoozed_until") and vals.get("trigger", default_trigger) == "auto"
            for vals in vals_list
        ):
            raise UserError(
                _(
                    "You can not create a snoozed orderpoint that is not manually triggered.",
                ),
            )
        return super().create(vals_list)

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "orderpoint.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        vals = self._update_vals_manual_qty_override(vals)
        if "company_id" in vals:
            for orderpoint in self:
                if orderpoint.company_id.id != vals["company_id"]:
                    raise UserError(
                        _(
                            "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one.",
                        ),
                    )
        if vals.get("snoozed_until"):
            new_trigger = vals.get("trigger")
            if any(
                (new_trigger or orderpoint.trigger) == "auto" for orderpoint in self
            ):
                raise UserError(
                    _(
                        "You can only snooze manual orderpoints. You should rather archive 'auto-trigger' orderpoints if you do not want them to be triggered.",
                    ),
                )
        if vals.get("trigger") == "auto" and "snoozed_until" not in vals:
            dbg.logic.debug(
                "write: trigger auto clears snoozed_until on %s", dbg.rec(self)
            )
            vals = dict(vals, snoozed_until=False)
        return super().write(vals)

    @api.depends("warehouse_id", "company_id")
    def _compute_allowed_location_ids(self):
        all_warehouses = self.env["stock.warehouse"].search([])
        orderpoints_by_key = defaultdict(
            lambda: self.env["stock.warehouse.orderpoint"],
        )
        for orderpoint in self:
            orderpoints_by_key[orderpoint.company_id, orderpoint.warehouse_id] |= (
                orderpoint
            )
        for (company, warehouse), orderpoints in orderpoints_by_key.items():
            loc_domain = Domain("usage", "in", ("internal", "view")) & Domain(
                "company_id",
                "in",
                [False, company.id],
            )
            for other_warehouse in all_warehouses:
                if other_warehouse == warehouse:
                    continue
                if other_warehouse.view_location_id:
                    loc_domain &= ~Domain(
                        "id",
                        "child_of",
                        other_warehouse.view_location_id.id,
                    )
            orderpoints.allowed_location_ids = self.env["stock.location"].search(  # noqa: E8507 - already batched: one query per (company, warehouse), not per orderpoint
                loc_domain,
            )

    @api.depends("rule_ids")
    def _compute_show_supply_warning(self):
        for orderpoint in self:
            orderpoint.show_supply_warning = not orderpoint.rule_ids

    @api.depends(
        "route_id",
        "product_id",
        "location_id",
        "company_id",
        "warehouse_id",
        "product_id.route_ids",
    )
    def _compute_rule_ids(self):
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: orderpoint.product_id and orderpoint.location_id,
        )
        rules_cache = {}
        extra_routes = orderpoints_to_compute.product_id._get_total_routes_by_product()
        for orderpoint in orderpoints_to_compute:
            all_product_routes = (
                orderpoint.product_id.route_ids
                | orderpoint.product_id.categ_id.total_route_ids
                | extra_routes[orderpoint.product_id.id]
            )
            cache_key = (
                orderpoint.location_id,
                orderpoint.route_id,
                orderpoint.product_id.route_ids,
                all_product_routes,
            )
            if cache_key in rules_cache:
                rule_ids = rules_cache[cache_key]
            else:
                rule_ids = orderpoint.product_id._get_rules_from_location(
                    orderpoint.location_id,
                    route_ids=orderpoint.route_id,
                )
                rules_cache[cache_key] = rule_ids
            orderpoint.rule_ids = rule_ids
        (self - orderpoints_to_compute).rule_ids = False

    @api.depends("product_min_qty")
    def _compute_product_max_qty(self):
        for orderpoint in self:
            if (
                orderpoint.product_uom_id.compare(
                    orderpoint.product_max_qty, orderpoint.product_min_qty
                )
                < 0
                or not orderpoint.product_max_qty
            ):
                orderpoint.product_max_qty = orderpoint.product_min_qty

    @api.depends(
        "rule_ids",
        "route_id",
        "product_id",
        "product_id.seller_ids",
        "product_id.seller_ids.product_uom_id",
    )
    def _compute_allowed_replenishment_uom_ids(self):
        for orderpoint in self:
            orderpoint.allowed_replenishment_uom_ids = orderpoint.product_id.uom_ids
            if "buy" in orderpoint.rule_ids.mapped("action"):
                orderpoint.allowed_replenishment_uom_ids += (
                    orderpoint.product_id.seller_ids.product_uom_id
                )

    @api.depends(
        "allowed_replenishment_uom_ids", "replenishment_uom_id", "qty_to_order"
    )
    @api.depends_context("global_horizon_days")
    def _compute_replenishment_uom_id_placeholder(self):
        alternatives = self._get_replenishment_multiple_alternative_map(
            {orderpoint.id: orderpoint.qty_to_order for orderpoint in self},
        )
        for orderpoint in self:
            alternative = alternatives.get(orderpoint.id)
            orderpoint.replenishment_uom_id_placeholder = (
                alternative.display_name if alternative else ""
            )

    def _get_default_warehouse_by_company(self, companies):
        warehouses = self.env["stock.warehouse"].search(
            [("company_id", "in", companies.ids)],
            order="company_id, sequence, id",
        )
        default_by_company = {}
        for warehouse in warehouses:
            default_by_company.setdefault(warehouse.company_id.id, warehouse)
        return default_by_company

    @api.depends("location_id", "company_id")
    def _compute_warehouse_id(self):
        default_by_company = self._get_default_warehouse_by_company(self.company_id)
        for orderpoint in self:
            if orderpoint.location_id.warehouse_id:
                orderpoint.warehouse_id = orderpoint.location_id.warehouse_id
            elif orderpoint.company_id:
                orderpoint.warehouse_id = default_by_company.get(
                    orderpoint.company_id.id,
                    self.env["stock.warehouse"],
                )
            if not orderpoint.warehouse_id:
                self.env["stock.warehouse"]._raise_missing_warehouse()

    @api.depends("warehouse_id", "company_id")
    def _compute_location_id(self):
        default_by_company = self._get_default_warehouse_by_company(
            (self - self.filtered("warehouse_id")).company_id,
        )
        for orderpoint in self:
            warehouse = orderpoint.warehouse_id or default_by_company.get(
                orderpoint.company_id.id,
                self.env["stock.warehouse"],
            )
            current = orderpoint.location_id
            # An editable default, so a stored location that still sits inside
            # the warehouse is the user's and is kept. Assigning unconditionally
            # reset a rule pointed at a particular shelf back to the warehouse's
            # stock location on any write of `warehouse_id` -- including one
            # that changed nothing, since `modified()` fires on the key and not
            # on a change. A location outside the warehouse is re-derived,
            # because that is what a real warehouse change invalidates.
            if (
                current
                and warehouse
                and current._is_child_of(warehouse.view_location_id)
            ):
                continue
            orderpoint.location_id = warehouse.lot_stock_id.id

    @api.depends("product_id", "qty_to_order", "product_max_qty")
    @api.depends_context("global_horizon_days")
    def _compute_unwanted_replenish(self):
        for orderpoint in self:
            if (
                not orderpoint.product_id
                or orderpoint.product_uom_id.is_zero(orderpoint.qty_to_order)
                or orderpoint.product_uom_id.compare(orderpoint.product_max_qty, 0)
                == -1
            ):
                orderpoint.unwanted_replenish = False
            else:
                after_replenish_qty = (
                    orderpoint.product_id.with_context(
                        company_id=orderpoint.company_id.id,
                        location=orderpoint.location_id.id,
                    ).qty_available_virtual
                    + orderpoint.qty_to_order
                )
                orderpoint.unwanted_replenish = (
                    orderpoint.product_uom_id.compare(
                        after_replenish_qty,
                        orderpoint.product_max_qty,
                    )
                    > 0
                )

    @api.depends(
        "product_id",
        "product_id.categ_id",
        "product_id.route_ids",
        "product_id.categ_id.route_ids",
        "location_id",
    )
    def _compute_route_id_placeholder(self):
        default_routes = self._get_default_route_map()
        empty_route = self.env["stock.route"]
        for orderpoint in self:
            default_route = default_routes.get(orderpoint.id, empty_route)
            orderpoint.route_id_placeholder = (
                default_route.display_name if default_route else ""
            )

    @api.depends(
        "route_id",
        "product_id",
        "product_id.categ_id",
        "product_id.route_ids",
        "product_id.categ_id.route_ids",
        "location_id",
    )
    def _compute_effective_route_id(self):
        default_routes = self.filtered(
            lambda orderpoint: not orderpoint.route_id,
        )._get_default_route_map()
        empty_route = self.env["stock.route"]
        for orderpoint in self:
            orderpoint.effective_route_id = orderpoint.route_id or default_routes.get(
                orderpoint.id,
                empty_route,
            )

    def _get_qty_forecast_map(self):
        values_by_orderpoint = self._read_product_qty_by_context(
            ["qty_available_virtual"],
        )
        qty_in_progress = self._get_quantity_in_progress()
        return {
            orderpoint.id: (
                values_by_orderpoint[orderpoint.id]["qty_available_virtual"]
                + qty_in_progress[orderpoint.id]
            )
            for orderpoint in self
        }

    @dbg.timed
    def _read_product_qty_by_context(self, field_names):
        result = {}
        orderpoints_by_context = defaultdict(self.browse)
        for orderpoint in self:
            orderpoints_by_context[
                frozendict(orderpoint._prepare_product_context())
            ] |= orderpoint
        dbg.performance.debug(
            "_read_product_qty_by_context(%s): %d orderpoints in %d contexts",
            field_names,
            len(self),
            len(orderpoints_by_context),
        )
        for product_context, orderpoints in orderpoints_by_context.items():
            values_by_product = {
                values["id"]: values
                for values in orderpoints.product_id.with_context(
                    product_context,
                ).read(field_names)
            }
            for orderpoint in orderpoints:
                result[orderpoint.id] = values_by_product[orderpoint.product_id.id]
        return result

    @api.depends(
        "product_id",
        "location_id",
        "product_id.qty_available",
        "product_id.qty_available_virtual",
        "product_id.seller_ids.delay",
    )
    @dbg.timed
    @api.depends_context("global_horizon_days")
    def _compute_qty(self):
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: orderpoint.product_id and orderpoint.location_id,
        )
        excluded = self - orderpoints_to_compute
        excluded.qty_on_hand = 0.0
        excluded.qty_forecast = 0.0
        if not orderpoints_to_compute:
            return
        values_by_orderpoint = orderpoints_to_compute._read_product_qty_by_context(
            ["qty_available"],
        )
        qty_forecast = orderpoints_to_compute._get_qty_forecast_map()
        for orderpoint in orderpoints_to_compute:
            orderpoint.qty_on_hand = values_by_orderpoint[orderpoint.id][
                "qty_available"
            ]
            orderpoint.qty_forecast = qty_forecast[orderpoint.id]
            dbg.logic.debug(
                "[orderpoint:%s] on hand %s, forecast %s",
                orderpoint.id,
                orderpoint.qty_on_hand,
                orderpoint.qty_forecast,
            )

    @api.depends(
        "qty_to_order_manual",
        "qty_to_order_computed",
        "qty_to_order_manual_set",
    )
    @api.depends_context("global_horizon_days")
    def _compute_qty_to_order(self):
        what_if = self._get_horizon_suggestion_map()
        for orderpoint in self:
            if orderpoint.qty_to_order_manual_set:
                orderpoint.qty_to_order = orderpoint.qty_to_order_manual
            else:
                orderpoint.qty_to_order = what_if.get(
                    orderpoint.id,
                    orderpoint.qty_to_order_computed,
                )

    def _get_horizon_suggestion_map(self):
        override = self.env.context.get("global_horizon_days")
        if override is None:
            return {}
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: (
                not orderpoint.qty_to_order_manual_set
                and override != orderpoint._get_canonical_horizon_days()
            ),
        )
        if not orderpoints_to_compute:
            return {}
        return orderpoints_to_compute._get_qty_to_order_map()

    @api.depends(
        "replenishment_uom_id",
        "product_min_qty",
        "product_max_qty",
        "product_id",
        "location_id",
        "rule_ids",
        "product_id.seller_ids.delay",
        "company_id.horizon_days",
    )
    @dbg.timed
    def _compute_qty_to_order_computed(self):
        canonical = self._with_canonical_horizon()
        suggestions = canonical._get_qty_to_order_map()
        for orderpoint in canonical:
            orderpoint.qty_to_order_computed = suggestions[orderpoint.id]

    def _inverse_route_id(self):
        pass

    def _inverse_qty_to_order(self):
        suggestions = self._with_canonical_horizon()._get_qty_to_order_map()
        overridden = self.browse()
        for orderpoint in self:
            if orderpoint.trigger != "auto" and orderpoint.product_uom_id.compare(
                orderpoint.qty_to_order,
                suggestions.get(orderpoint.id, orderpoint.qty_to_order_computed),
            ):
                overridden |= orderpoint
        by_quantity = defaultdict(self.browse)
        for orderpoint in overridden:
            by_quantity[orderpoint.qty_to_order] |= orderpoint
        if overridden:
            dbg.logic.debug(
                "_inverse_qty_to_order: manual override on %s", dbg.rec(overridden)
            )
        for quantity, group in by_quantity.items():
            group.write(
                {"qty_to_order_manual_set": True, "qty_to_order_manual": quantity},
            )
        (self - overridden).write(
            {"qty_to_order_manual_set": False, "qty_to_order_manual": 0},
        )

    def _get_domain_unset_route_candidate(self, routes, match_unset):
        domain = Domain("route_id", "=", False)
        if match_unset or not routes:
            return domain
        return domain & (
            Domain("product_id.route_ids", "in", routes.ids)
            | Domain("product_id.categ_id.route_ids", "in", routes.ids)
        )

    def _search_effective_route_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        Route = self.env["stock.route"]
        match_unset = False
        if operator == "any":
            routes = Route.search(
                value if isinstance(value, Domain) else [("id", "in", value)],
            )
        elif operator == "in":
            ids = set(value)
            match_unset = False in ids or None in ids
            routes = Route.browse(id_ for id_ in ids if id_)
        else:
            routes = Route.search([("display_name", operator, value)])
        unset_orderpoints = self.env["stock.warehouse.orderpoint"].search(
            self._get_domain_unset_route_candidate(routes, match_unset),
        )
        default_routes = unset_orderpoints._get_default_route_map()
        empty_route = Route
        matched_ids = [
            orderpoint.id
            for orderpoint in unset_orderpoints
            if (
                (default_route := default_routes.get(orderpoint.id, empty_route))
                and default_route in routes
            )
            or (match_unset and not default_route)
        ]
        return Domain("route_id", "in", routes.ids) | Domain("id", "in", matched_ids)

    def _search_qty_to_order(self, operator, value):
        if DOMAIN_PREDICATES.get(operator) is None:
            return NotImplemented
        return Domain(
            [
                "|",
                "&",
                ("qty_to_order_manual_set", "=", True),
                ("qty_to_order_manual", operator, value),
                "&",
                ("qty_to_order_manual_set", "=", False),
                ("qty_to_order_computed", operator, value),
            ],
        )
