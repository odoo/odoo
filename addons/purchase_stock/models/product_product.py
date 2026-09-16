import operator as py_operator
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round

_SUGGESTED_QTY_OPERATORS = {
    "=": py_operator.eq,
    "!=": py_operator.ne,
    "<": py_operator.lt,
    "<=": py_operator.le,
    ">": py_operator.gt,
    ">=": py_operator.ge,
}


_debug = DebugLog(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    purchase_order_line_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="product_id",
        string="PO Lines",
    )
    monthly_demand = fields.Float(compute="_compute_monthly_demand")
    suggested_qty = fields.Integer(
        compute="_compute_suggested_qty",
        search="_search_suggested_qty",
    )
    suggest_estimated_price = fields.Float(compute="_compute_suggest_estimated_price")

    @api.depends_context(
        "suggest_based_on",
        "suggest_days",
        "suggest_percent",
        "warehouse_id",
    )
    @api.depends("monthly_demand")
    def _compute_suggested_qty(self):
        _debug.perf.count("suggested_qty_compute", products=self)
        ctx = self.env.context
        self.suggested_qty = 0
        if ctx.get("suggest_based_on") == "actual_demand":
            for product in self:
                if product.qty_available_virtual >= 0:
                    continue
                qty = (
                    -product.qty_available_virtual * ctx.get("suggest_percent", 0) / 100
                )
                product.suggested_qty = max(
                    float_round(qty, precision_digits=0, rounding_method="UP"),
                    0,
                )
        elif ctx.get("suggest_based_on"):
            for product in self:
                if product.monthly_demand <= 0:
                    continue
                monthly_ratio = ctx.get("suggest_days", 0) / (365.25 / 12)
                qty = (
                    product.monthly_demand
                    * monthly_ratio
                    * ctx.get("suggest_percent", 0)
                    / 100
                )
                qty -= max(product.qty_available, 0) + max(product.qty_incoming, 0)
                product.suggested_qty = max(
                    float_round(qty, precision_digits=0, rounding_method="UP"),
                    0,
                )

    @api.depends_context(
        "suggest_based_on",
        "suggest_days",
        "suggest_percent",
        "warehouse_id",
    )
    @api.depends("suggested_qty")
    def _compute_suggest_estimated_price(self):
        _debug.perf.count("suggest_price_compute", products=self)
        seller_args = {
            "partner_id": self.env["res.partner"].browse(
                self.env.context.get("partner_id"),
            ),
            "params": {
                "order_id": self.env["purchase.order"].browse(
                    self.env.context.get("order_id"),
                ),
            },
        }
        self.suggest_estimated_price = 0.0
        for product in self:
            if product.suggested_qty <= 0:
                continue
            seller = product._select_seller(
                quantity=product.suggested_qty,
                **seller_args,
            ) or product._select_seller(
                quantity=None,
                ordered_by="min_qty",
                **seller_args,
            )
            price = seller.price_discounted if seller else product.standard_price
            product.suggest_estimated_price = price * product.suggested_qty

    @api.depends_context("suggest_days", "suggest_based_on", "warehouse_id")
    def _compute_quantities(self):
        return super()._compute_quantities()

    @api.depends_context("suggest_based_on", "warehouse_id")
    def _compute_monthly_demand(self):
        _debug.perf.count("monthly_demand_compute", products=self)
        based_on = self.env.context.get("suggest_based_on", "30_days")
        start_date, limit_date = self._get_monthly_demand_range(based_on)
        move_domain = Domain(
            [
                ("product_id", "in", self.ids),
                (
                    "state",
                    "in",
                    ["assigned", "confirmed", "partially_available", "done"],
                ),
                ("date", ">=", start_date),
                ("date", "<", limit_date),
            ],
        )
        move_domain = Domain.AND(
            [
                move_domain,
                self._get_domain_monthly_demand_moves_location(),
            ],
        )
        with _debug.perf(
            "monthly_demand_aggregate",
            cr=self.env.cr,
            products=self,
            based_on=based_on,
        ):
            move_qty_by_products = self.env["stock.move"]._read_group(
                move_domain,
                ["product_id"],
                ["product_qty:sum"],
            )
        qty_by_product = {product.id: qty for product, qty in move_qty_by_products}
        factor = 1

        if based_on == "one_year":
            factor = 12
        elif based_on in {"three_months", "last_year_quarter"}:
            factor = 3
        elif based_on == "one_week":
            factor = 7 / (365.25 / 12)

        for product in self:
            product.monthly_demand = qty_by_product.get(product.id, 0) / factor

    def _search_suggested_qty(self, operator, value):
        if operator not in _SUGGESTED_QTY_OPERATORS:
            return NotImplemented

        search_domain = Domain(
            self.env.context.get("suggest_domain") or [("type", "=", "consu")]
        )

        def remove_self_reference(condition):
            if condition.field_expr == "suggested_qty":
                return Domain.TRUE
            return condition

        safe_search_domain = search_domain.map_conditions(remove_self_reference)
        products = self.search_fetch(safe_search_domain, ["suggested_qty"])

        compare = _SUGGESTED_QTY_OPERATORS[operator]
        ids = [
            product.id for product in products if compare(product.suggested_qty, value)
        ]
        return [("id", "in", ids)]

    def _get_domain_lines(self, location_ids=False, warehouse_ids=False):
        domains = []
        rfq_domain = Domain("state", "=", "draft") & Domain(
            "product_id",
            "in",
            self.ids,
        )
        if location_ids:
            domains.append(
                Domain(
                    [
                        "|",
                        "&",
                        ("orderpoint_id", "=", False),
                        "|",
                        "&",
                        ("location_final_id", "=", False),
                        (
                            "order_id.picking_type_id.default_location_dest_id",
                            "in",
                            location_ids,
                        ),
                        "&",
                        ("move_ids", "=", False),
                        ("location_final_id", "child_of", location_ids),
                        "&",
                        ("move_dest_ids", "=", False),
                        ("orderpoint_id.location_id", "in", location_ids),
                    ],
                ),
            )
        if warehouse_ids:
            domains.append(
                Domain(
                    [
                        "|",
                        "&",
                        ("orderpoint_id", "=", False),
                        ("order_id.picking_type_id.warehouse_id", "in", warehouse_ids),
                        "&",
                        ("move_dest_ids", "=", False),
                        ("orderpoint_id.warehouse_id", "in", warehouse_ids),
                    ],
                ),
            )
        return rfq_domain & Domain.OR(domains or [Domain.TRUE])

    @api.model
    def _get_domain_monthly_demand_moves_location(self):
        warehouse_id = self.env.context.get("warehouse_id")
        non_return_moves_domain = [
            "!",
            ("move_dest_ids.origin_returned_move_id", "=", False),
        ]
        if not warehouse_id:
            return Domain.AND(
                [
                    Domain.OR(
                        [
                            [("location_dest_usage", "in", ["customer", "production"])],
                            [
                                (
                                    "location_final_id.usage",
                                    "in",
                                    ["customer", "production"],
                                )
                            ],
                        ],
                    ),
                    non_return_moves_domain,
                ],
            )
        else:
            return Domain.AND(
                [
                    [("location_id.warehouse_id", "=", warehouse_id)],
                    Domain.OR(
                        [
                            [("location_dest_id.warehouse_id", "!=", warehouse_id)],
                            [("location_final_id.warehouse_id", "!=", warehouse_id)],
                        ],
                    ),
                    [("location_dest_id.usage", "!=", "inventory")],
                    non_return_moves_domain,
                ],
            )

    def _get_monthly_demand_range(self, based_on):
        _debug.logic("monthly_demand_range", products=self, based_on=based_on)
        start_date = limit_date = datetime.now()

        if not based_on or based_on in {"actual_demand", "30_days"}:
            start_date -= relativedelta(days=30)
        elif based_on == "one_week":
            start_date -= relativedelta(weeks=1)
        elif based_on == "three_months":
            start_date -= relativedelta(months=3)
        elif based_on == "one_year":
            start_date -= relativedelta(years=1)
        else:
            today = datetime.now()
            start_date = datetime(year=today.year - 1, month=today.month, day=1)

            if based_on == "last_year_m_plus_1":
                start_date += relativedelta(months=1)
            elif based_on == "last_year_m_plus_2":
                start_date += relativedelta(months=2)

            if based_on == "last_year_quarter":
                limit_date = start_date + relativedelta(months=3)
            else:
                limit_date = start_date + relativedelta(months=1)

        return start_date, limit_date

    def _get_quantity_in_progress(self, location_ids=False, warehouse_ids=False):
        _debug.logic("qty_in_progress_read", products=self)
        if not location_ids:
            location_ids = []
        if not warehouse_ids:
            warehouse_ids = []

        qty_by_product_location, qty_by_product_wh = super()._get_quantity_in_progress(
            location_ids,
            warehouse_ids,
        )
        domain = self._get_domain_lines(location_ids, warehouse_ids)
        groups = (
            self.env["purchase.order.line"]
            .sudo()
            ._read_group(
                domain,
                [
                    "order_id",
                    "product_id",
                    "product_uom_id",
                    "orderpoint_id",
                    "location_final_id",
                ],
                ["product_qty:sum"],
            )
        )
        for order, product, uom, orderpoint, location_final, product_qty_sum in groups:
            if orderpoint:
                location = orderpoint.location_id
            elif location_final:
                location = location_final
            else:
                location = order.picking_type_id.default_location_dest_id
            product_qty = uom._get_quantity_estimate(
                product_qty_sum,
                product.uom_id,
                round=False,
            )
            qty_by_product_location[(product.id, location.id)] += product_qty
            qty_by_product_wh[(product.id, location.warehouse_id.id)] += product_qty
        return qty_by_product_location, qty_by_product_wh

    def _get_total_routes_by_product(self):
        result = super()._get_total_routes_by_product()
        buy_routes = self.env["stock.rule"]._get_buy_routes()
        if buy_routes:
            for product in self:
                if product.seller_ids:
                    result[product.id] |= buy_routes
        return result

    def _prepare_quantities_vals(self, filters, location_domains=None):
        if (
            self.env.context.get("suggest_based_on")
            and "suggest_days" in self.env.context
        ):
            filters = filters._replace(
                to_date=fields.Datetime.now()
                + relativedelta(days=self.env.context.get("suggest_days")),
            )
        return super()._prepare_quantities_vals(
            filters, location_domains=location_domains
        )

    def _get_order_lead_days(self, delays):
        return delays.get("purchase_delay", 0.0)
