from datetime import datetime, time
from json import dumps

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.numbers import float_round
from odoo.tools.misc import format_date

from ..tools import debug_log as dbg


class StockReplenishmentInfo(models.TransientModel):
    _name = "stock.replenishment.info"
    _description = "Stock supplier replenishment information"
    _rec_name = "orderpoint_id"

    _DEMAND_MOVE_STATES = ("assigned", "confirmed", "partially_available", "done")

    orderpoint_id = fields.Many2one(comodel_name="stock.warehouse.orderpoint")
    product_id = fields.Many2one(
        comodel_name="product.product",
        related="orderpoint_id.product_id",
    )
    product_uom_name = fields.Char(related="orderpoint_id.product_uom_name")
    product_min_qty = fields.Float(
        related="orderpoint_id.product_min_qty",
        string="Min",
        related_sudo=False,
        readonly=False,
        required=True,
    )
    product_max_qty = fields.Float(
        related="orderpoint_id.product_max_qty",
        string="Max",
        related_sudo=False,
        readonly=False,
        required=True,
    )
    qty_to_order = fields.Float(related="orderpoint_id.qty_to_order")
    json_lead_days = fields.Char(compute="_compute_json_lead_days")
    json_replenishment_graph = fields.Char(compute="_compute_json_replenishment_graph")
    based_on = fields.Selection(
        selection=[
            ("one_week", "Last 7 days"),
            ("one_month", "Last 30 days"),
            ("three_months", "Last 3 months"),
            ("one_year", "Last 12 months"),
            ("last_year", "Same month last year"),
            ("last_year_2", "Next month last year"),
            ("last_year_3", "After next month last year"),
            ("last_year_quarter", "Last year quarter"),
        ],
        string="Based on",
        default="one_month",
        required=True,
        help="Estimate the sales volume for the period based on past period or order the forecasted quantity for that period.",
    )
    percent_factor = fields.Integer(
        default=100,
        required=True,
    )

    warehouseinfo_ids = fields.One2many(
        related="orderpoint_id.warehouse_id.resupply_route_ids"
    )
    wh_replenishment_option_ids = fields.One2many(
        comodel_name="stock.replenishment.option",
        inverse_name="replenishment_info_id",
    )

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        wizards._create_wh_replenishment_options()
        return wizards

    @api.constrains("percent_factor")
    def _check_percent_factor(self):
        if any(report.percent_factor < 0 for report in self):
            raise ValidationError(_("The percentage factor cannot be negative."))

    def _create_wh_replenishment_options(self):
        option_vals = []
        for replenishment_info in self:
            product = replenishment_info.product_id
            routes = sorted(
                replenishment_info.warehouseinfo_ids,
                key=lambda route: (
                    product.with_context(
                        location=route.supplier_wh_id.lot_stock_id.id,
                    ).qty_free
                ),
                reverse=True,
            )
            option_vals += [
                {
                    "product_id": product.id,
                    "route_id": route.id,
                    "replenishment_info_id": replenishment_info.id,
                }
                for route in routes
            ]
            dbg.logic.debug(
                "replenishment info %s: %d warehouse routes for product %s",
                replenishment_info.id,
                len(routes),
                product.id,
            )
        self.env["stock.replenishment.option"].create(option_vals)

    def _get_lead_days_and_description(self):
        self.check_singleton()
        orderpoint = self.orderpoint_id
        orderpoints_values = orderpoint._prepare_lead_time_params()
        return orderpoint.rule_ids.with_context(
            global_horizon_days=orderpoint._get_horizon_days(),
        )._get_lead_days(
            orderpoint.product_id,
            **orderpoints_values,
        )

    @api.depends("orderpoint_id")
    @api.depends_context("lang")
    def _compute_json_lead_days(self):
        def _format_description(description):
            formatted_description = []
            intermediary_date = fields.Date.today()
            for line in reversed(description):
                if isinstance(line[1], str):
                    formatted_description.append((line[0], line[1], False))
                else:
                    intermediary_date += relativedelta(days=int(line[1]))
                    formatted_description.append(
                        (line[0], format_date(self.env, intermediary_date), True)
                    )
            return formatted_description

        qty_to_html = self.env["ir.qweb.field.float"].value_to_html
        precision = {"decimal_precision": "Product Unit"}

        self.json_lead_days = False
        for replenishment_report in self:
            if (
                not replenishment_report.product_id
                or not replenishment_report.orderpoint_id.location_id
            ):
                continue
            orderpoint = replenishment_report.orderpoint_id
            __, lead_days_description = (
                replenishment_report._get_lead_days_and_description()
            )
            if lead_days_description:
                lead_days_description = _format_description(lead_days_description)
            replenishment_report.json_lead_days = dumps(
                {
                    "lead_horizon_date": format_date(
                        self.env, orderpoint.lead_horizon_date
                    ),
                    "lead_days_description": lead_days_description,
                    "today": format_date(self.env, fields.Date.today()),
                    "trigger": orderpoint.trigger,
                    "qty_forecast": qty_to_html(orderpoint.qty_forecast, precision),
                    "qty_to_order": qty_to_html(orderpoint.qty_to_order, precision),
                    "product_min_qty": qty_to_html(
                        orderpoint.product_min_qty, precision
                    ),
                    "product_max_qty": qty_to_html(
                        orderpoint.product_max_qty, precision
                    ),
                    "product_uom_name": orderpoint.product_uom_name,
                    "virtual": orderpoint.trigger == "manual"
                    and orderpoint.create_uid.id == SUPERUSER_ID,
                }
            )

    def _get_period_of_time(self):
        self.check_singleton()
        today = fields.Datetime.now()
        start_date = limit_date = today
        if self.based_on == "one_week":
            start_date -= relativedelta(weeks=1)
        elif self.based_on == "one_month":
            start_date -= relativedelta(months=1)
        elif self.based_on == "three_months":
            start_date -= relativedelta(months=3)
        elif self.based_on == "one_year":
            start_date -= relativedelta(years=1)
        else:
            start_date = datetime(year=today.year - 1, month=today.month, day=1)
            if self.based_on == "last_year_2":
                start_date += relativedelta(months=1)
            elif self.based_on == "last_year_3":
                start_date += relativedelta(months=2)
            if self.based_on == "last_year_quarter":
                limit_date = start_date + relativedelta(months=3)
            else:
                limit_date = start_date + relativedelta(months=1)
        return start_date, limit_date

    @api.model
    def _prepare_graph_data(self, product_min_qty, product_max_qty, daily_demand=0):
        if not daily_demand:
            ordering_period = 0
            x_axis_vals = ["", " "]
            curve_line_vals = []
        else:
            qty_diff = product_max_qty - product_min_qty or 1
            ordering_period = max(1, int(qty_diff / daily_demand))
            x_axis_vals = [""]
            curve_line_vals = [{"x": "", "y": product_max_qty}]
            for i in range(1, 4):
                date_string = _("In %s day(s)", int(i * ordering_period))
                x_axis_vals.append(date_string)
                curve_line_vals.append({"x": date_string, "y": product_min_qty})
                curve_line_vals.append({"x": date_string, "y": product_max_qty})
            curve_line_vals.pop()

        max_line_vals = [{"x": date, "y": product_max_qty} for date in x_axis_vals]
        min_line_vals = [{"x": date, "y": product_min_qty} for date in x_axis_vals]
        graph_data = {
            "x_axis_vals": x_axis_vals,
            "max_line_vals": max_line_vals,
            "min_line_vals": min_line_vals,
            "curve_line_vals": curve_line_vals,
        }
        return ordering_period, graph_data

    @api.depends(
        "orderpoint_id",
        "based_on",
        "percent_factor",
        "product_min_qty",
        "product_max_qty",
    )
    def _compute_json_replenishment_graph(self):
        self.json_replenishment_graph = False
        for replenishment_report in self:
            if (
                not replenishment_report.product_id
                or not replenishment_report.orderpoint_id.location_id
            ):
                continue
            lead_days, __ = replenishment_report.with_context(
                bypass_delay_description=True
            )._get_lead_days_and_description()
            date_from, date_to = replenishment_report._get_period_of_time()
            domain = Domain.AND(
                [
                    [("product_id", "=", replenishment_report.product_id.id)],
                    [("date", ">=", date_from)],
                    [("date", "<=", datetime.combine(date_to, time.max))],
                    [("state", "in", self._DEMAND_MOVE_STATES)],
                    [
                        (
                            "company_id",
                            "=",
                            replenishment_report.orderpoint_id.company_id.id,
                        ),
                    ],
                ],
            )
            quantity_out = (
                self.env["stock.move"]._read_group(  # noqa: E8507 - the domain carries this record's own product, period and company
                    Domain.AND(
                        [
                            domain,
                            [
                                (
                                    "location_dest_id.usage",
                                    "in",
                                    ["customer", "production"],
                                )
                            ],
                        ]
                    ),
                    aggregates=["product_qty:sum"],
                )[0][0]
                or 0.0
            )
            quantity_returned = (
                self.env["stock.move"]._read_group(  # noqa: E8507 - the domain carries this record's own product, period and company
                    Domain.AND([domain, [("location_id.usage", "=", "customer")]]),
                    aggregates=["product_qty:sum"],
                )[0][0]
                or 0.0
            )

            product_min_qty = replenishment_report.product_min_qty
            product_max_qty = replenishment_report.product_max_qty
            average_stock = (product_min_qty + product_max_qty) / 2
            lead_time = lead_days.get("total_delay", 0)
            daily_demand = (
                (quantity_out - quantity_returned) / (date_to - date_from).days
            ) * (replenishment_report.percent_factor / 100)

            ordering_period, graph_data = replenishment_report._prepare_graph_data(
                product_min_qty, product_max_qty, daily_demand=daily_demand
            )
            replenishment_report.json_replenishment_graph = dumps(
                {
                    "product_uom_name": replenishment_report.product_uom_name,
                    "product_max_qty": product_max_qty,
                    "product_min_qty": product_min_qty,
                    "qty_on_hand": replenishment_report.orderpoint_id.qty_on_hand,
                    "lead_time": lead_time,
                    "daily_demand": float_round(
                        daily_demand,
                        precision_rounding=replenishment_report.product_id.uom_id.rounding,
                    ),
                    "average_stock": float_round(
                        average_stock,
                        precision_rounding=replenishment_report.product_id.uom_id.rounding,
                    ),
                    "ordering_period": float_round(
                        ordering_period, precision_rounding=1
                    ),
                    "x_axis_vals": graph_data["x_axis_vals"],
                    "max_line_vals": graph_data["max_line_vals"],
                    "min_line_vals": graph_data["min_line_vals"],
                    "curve_line_vals": graph_data["curve_line_vals"],
                },
            )


class StockReplenishmentOption(models.TransientModel):
    _name = "stock.replenishment.option"
    _description = "Stock warehouse replenishment option"

    route_id = fields.Many2one(comodel_name="stock.route")
    product_id = fields.Many2one(comodel_name="product.product")
    replenishment_info_id = fields.Many2one(comodel_name="stock.replenishment.info")
    location_id = fields.Many2one(
        comodel_name="stock.location",
        related="warehouse_id.lot_stock_id",
    )
    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        related="route_id.supplier_wh_id",
    )
    uom = fields.Char(related="product_id.uom_name")
    qty_to_order = fields.Float(related="replenishment_info_id.qty_to_order")
    qty_free = fields.Float(compute="_compute_qty_free")
    lead_time = fields.Char(compute="_compute_lead_time")
    warning_message = fields.Char(compute="_compute_warning_message")

    @api.depends("product_id", "route_id")
    def _compute_qty_free(self):
        for record in self:
            record.qty_free = record.product_id.with_context(
                location=record.location_id.id
            ).qty_free

    @api.depends("replenishment_info_id")
    def _compute_lead_time(self):
        for record in self:
            rule = self.env["stock.rule"]._get_rule(
                record.product_id,
                record.location_id,
                {
                    "route_ids": record.route_id,
                    "warehouse_id": record.warehouse_id,
                },
            )
            delay = (
                rule._get_lead_days(record.product_id)[0]["total_delay"] if rule else 0
            )
            record.lead_time = _("%s days", delay)

    @api.depends("warehouse_id", "qty_free", "uom", "qty_to_order")
    def _compute_warning_message(self):
        self.warning_message = ""
        for record in self:
            if (
                record.product_id.uom_id.compare(record.qty_free, record.qty_to_order)
                < 0
            ):
                record.warning_message = _(
                    "%(warehouse)s can only provide %(free_qty)s %(uom)s, while the quantity to order is %(qty_to_order)s %(uom)s.",
                    warehouse=record.warehouse_id.name,
                    free_qty=record.qty_free,
                    uom=record.uom,
                    qty_to_order=record.qty_to_order,
                )

    def action_select_route(self):
        if self.product_id.uom_id.compare(self.qty_free, self.qty_to_order) < 0:
            dbg.logic.debug(
                "action_select_route: free %s < to order %s on route %s, warning",
                self.qty_free,
                self.qty_to_order,
                self.route_id.id,
            )
            return {
                "type": "ir.actions.act_window",
                "res_model": "stock.replenishment.option",
                "res_id": self.id,
                "views": [
                    [
                        self.env.ref("stock.replenishment_option_warning_view").id,
                        "form",
                    ],
                ],
                "target": "new",
                "name": _("Quantity available too low"),
            }
        return self.action_order_full_quantity()

    def action_order_available_quantity(self):
        dbg.lifecycle.debug(
            "[orderpoint:%s] route %s, qty_to_order capped to free %s",
            self.replenishment_info_id.orderpoint_id.id,
            self.route_id.id,
            self.qty_free,
        )
        self.replenishment_info_id.orderpoint_id.route_id = self.route_id
        self.replenishment_info_id.orderpoint_id.qty_to_order = self.qty_free
        return {"type": "ir.actions.act_window_close"}

    def action_order_full_quantity(self):
        dbg.lifecycle.debug(
            "[orderpoint:%s] route %s",
            self.replenishment_info_id.orderpoint_id.id,
            self.route_id.id,
        )
        self.replenishment_info_id.orderpoint_id.route_id = self.route_id
        return {"type": "ir.actions.act_window_close"}
