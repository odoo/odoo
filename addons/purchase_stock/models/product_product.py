from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = "product.product"

    purchase_order_line_ids = fields.One2many(
        comodel_name="purchase.order.line",
        inverse_name="product_id",
        string="PO Lines",
    )  # used to compute quantities
    monthly_demand = fields.Float(
        compute="_compute_monthly_demand",
    )
    suggested_qty = fields.Integer(
        compute="_compute_suggested_quantity",
        search="_search_product_with_suggested_quantity",
    )
    suggest_estimated_price = fields.Float(
        compute="_compute_suggest_estimated_price",
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends_context(
        "suggest_based_on",
        "suggest_days",
        "suggest_percent",
        "warehouse_id",
    )
    @api.depends("monthly_demand")
    def _compute_suggested_quantity(self):
        ctx = self.env.context
        self.suggested_qty = 0
        if ctx.get("suggest_based_on") == "actual_demand":
            for product in self:
                if product.virtual_available >= 0:
                    continue
                qty = -product.virtual_available * ctx.get("suggest_percent", 0) / 100
                product.suggested_qty = max(
                    float_round(qty, precision_digits=0, rounding_method="UP"),
                    0,
                )
        elif ctx.get("suggest_based_on"):
            for product in self:
                if product.monthly_demand <= 0:
                    continue
                monthly_ratio = ctx.get("suggest_days", 0) / (
                    365.25 / 12
                )  # eg. 7 days / (365.25 days/yr / 12 mth/yr) = 0.23 months
                qty = (
                    product.monthly_demand
                    * monthly_ratio
                    * ctx.get("suggest_percent", 0)
                    / 100
                )
                qty -= max(product.qty_available, 0) + max(product.incoming_qty, 0)
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
            # Get lowest price pricelist for suggested_qty or lowest min_qty pricelist
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
                self._get_monthly_demand_moves_location_domain(),
            ],
        )
        move_qty_by_products = self.env["stock.move"]._read_group(
            move_domain,
            ["product_id"],
            ["product_qty:sum"],
        )
        qty_by_product = {product.id: qty for product, qty in move_qty_by_products}
        factor = 1

        if based_on == "one_year":
            factor = 12
        elif based_on == "three_months" or based_on == "last_year_quarter":
            factor = 3
        elif based_on == "one_week":
            # 7 days / (365.25 days/yr / 12 mth/yr) = 0.23 months
            factor = 7 / (365.25 / 12)

        for product in self:
            product.monthly_demand = qty_by_product.get(product.id, 0) / factor

    # ------------------------------------------------------------
    # SEARCH METHODS
    # ------------------------------------------------------------

    def _search_product_with_suggested_quantity(self, operator, value):
        if operator in ["in", "not in"]:
            return NotImplemented

        search_domain = self.env.context.get("suggest_domain") or [
            ("type", "=", "consu"),
        ]
        safe_search_domain = [
            c if c[0] != "suggested_qty" else [1, "=", 1] for c in search_domain
        ]
        products = self.search_fetch(safe_search_domain, ["suggested_qty"])
        ids = products.filtered_domain([("suggested_qty", operator, value)]).ids
        return [("id", "in", ids)]

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _get_lines_domain(self, location_ids=False, warehouse_ids=False):
        domains = []
        rfq_domain = Domain("state", "in", ("draft", "sent", "to approve")) & Domain(
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
    def _get_monthly_demand_moves_location_domain(self):
        """Returns a domain on stock moves coming from the selected warehouse that are:
            - going to customer locations or used in production
            - going to other warehouses (eg. central warehouse dispatching to stores)
        (We don't include returns in demand estimation - they come back on hand)
        """
        warehouse_id = self.env.context.get("warehouse_id")
        if not warehouse_id:
            return Domain.OR(
                [
                    [("location_dest_usage", "in", ["customer", "production"])],
                    [("location_final_id.usage", "in", ["customer", "production"])],
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
                    ),  # includes moves going to customer or production
                    [("location_dest_id.usage", "!=", "inventory")],  # exclude scrap
                ],
            )

    def _get_monthly_demand_range(self, based_on):
        start_date = limit_date = datetime.now()

        if not based_on or based_on == "actual_demand" or based_on == "30_days":
            start_date = start_date - relativedelta(days=30)  # Default monthly demand
        elif based_on == "one_week":
            start_date = start_date - relativedelta(weeks=1)
        elif based_on == "three_months":
            start_date = start_date - relativedelta(months=3)
        elif based_on == "one_year":
            start_date = start_date - relativedelta(years=1)
        else:  # Relative period of time.
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
        if not location_ids:
            location_ids = []
        if not warehouse_ids:
            warehouse_ids = []

        qty_by_product_location, qty_by_product_wh = super()._get_quantity_in_progress(
            location_ids,
            warehouse_ids,
        )
        domain = self._get_lines_domain(location_ids, warehouse_ids)
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
            product_qty = uom._compute_quantity(
                product_qty_sum,
                product.uom_id,
                round=False,
            )
            qty_by_product_location[(product.id, location.id)] += product_qty
            qty_by_product_wh[(product.id, location.warehouse_id.id)] += product_qty
        return qty_by_product_location, qty_by_product_wh

    def get_total_routes(self):
        routes = super().get_total_routes()
        if self.seller_ids:
            buy_routes = (
                self.env["stock.rule"].search([("action", "=", "buy")]).route_id
            )
            routes |= buy_routes
        return routes

    def _prepare_quantities_vals(
        self,
        lot_id,
        owner_id,
        package_id,
        from_date=False,
        to_date=False,
    ):
        if (
            self.env.context.get("suggest_based_on")
            and "suggest_days" in self.env.context
        ):
            # Override to compute actual demand suggestion and update forecast on Kanban card
            to_date = fields.Datetime.now() + relativedelta(
                days=self.env.context.get("suggest_days"),
            )
        return super()._prepare_quantities_vals(
            lot_id=lot_id,
            owner_id=owner_id,
            package_id=package_id,
            from_date=from_date,  # Keeping default which fetches all past deliveries
            to_date=to_date,
        )
