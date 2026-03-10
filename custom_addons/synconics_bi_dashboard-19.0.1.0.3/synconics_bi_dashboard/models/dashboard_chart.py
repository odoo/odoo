import io
import csv
import base64
import xlsxwriter
import imgkit
import logging

from math import gcd
from markupsafe import Markup
from types import SimpleNamespace
from collections import defaultdict
from datetime import datetime, timedelta, date, time
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.tools import groupby, format_amount
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class UTCDatetime:
    def __init__(self, dt):
        self.dt = dt

    def to_utc(self):
        return self  # Already handling as UTC

    def strftime(self, fmt):
        return self.dt.strftime(fmt)


def safe_datetime_combine(date_obj, time_obj):
    combined = datetime.combine(date_obj, time_obj)
    return UTCDatetime(combined)


def format_date_by_range(value, time_range):
    if not isinstance(value, (date, datetime)):
        return str(value)  # fallback if it's not a date/datetime

    if time_range == "day":
        return value.strftime("%d %B %Y")  # e.g., "19 June 2025"

    elif time_range == "week":
        return f"Week {value.isocalendar()[1]} {value.year}"  # e.g., "Week 25 2025"

    elif time_range == "month":
        return value.strftime("%B %Y")  # e.g., "June 2025"

    elif time_range == "quarter":
        # Calculate quarter from month
        quarter = (value.month - 1) // 3 + 1
        return f"Q{quarter} {value.year}"  # e.g., "Q2 2025"

    elif time_range == "year":
        return value.strftime("%Y")  # e.g., "2025"

    else:
        return str(value)  # default fallback


class DashboardChart(models.Model):
    _name = "dashboard.chart"
    _description = "Dashboard Charts"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.depends("list_field_ids", "list_field_ids.list_field_id")
    def _compute_used_list_fields(self):
        for rec in self:
            rec.used_list_field_ids = [
                (6, 0, rec.list_field_ids.mapped("list_field_id").ids)
            ]

    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    dashboard_id = fields.Many2one(
        "dashboard.dashboard",
        string="Dashboard",
        required=True,
        tracking=True,
        ondelete="cascade",
    )
    chart_type = fields.Selection(
        [
            ("kpi", "KPI"),
            ("tile", "Tile View"),
            ("bar_chart", "Bar Chart"),
            ("column_chart", "Column Chart"),
            ("doughnut_chart", "Doughnut Chart"),
            ("area_chart", "Area Chart"),
            ("funnel_chart", "Funnel Chart"),
            ("pyramid_chart", "Pyramid Chart"),
            ("line_chart", "Line Chart"),
            ("pie_chart", "Pie Chart"),
            ("radar_chart", "Radar Chart"),
            ("stackedcolumn_chart", "StackedColumn"),
            ("radial_chart", "Radial Chart"),
            ("scatter_chart", "Scatter Chart"),
            ("map_chart", "Map Chart"),
            ("meter_chart", "Meter Chart"),
            ("to_do", "To Do"),
            ("list", "List View"),
        ],
        default="kpi",
        required=True,
        string="Type",
        tracking=True,
    )

    # KPI fields
    kpi_model_id = fields.Many2one(
        "ir.model", string="Model ", ondelete="set null", tracking=True
    )
    kpi_model = fields.Char(string="Model Ref. ", related="kpi_model_id.model")
    kpi_data_type = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("average", "Average")],
        default="sum",
        string="Data Type ",
        tracking=True,
    )
    kpi_measurement_field_id = fields.Many2one(
        "ir.model.fields", string="Measure Field ", ondelete="set null", tracking=True
    )
    kpi_limit_record = fields.Integer(string="Limit Record", default=0)
    kpi_domain = fields.Char(string="Domain ", default="[]")
    kpi_date_filter_field_id = fields.Many2one(
        "ir.model.fields",
        string="Date Filter",
        ondelete="set null",
    )
    meter_target = fields.Integer(string="Target")
    kpi_date_filter_option = fields.Selection(
        [
            ("none", "None"),
            ("today", "Today"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("this_quarter", "This Quarter"),
            ("this_year", "This Year"),
            ("week_to_date", "Week To Date"),
            ("month_to_date", "Month To Date"),
            ("quarter_to_date", "Quarter To Date"),
            ("year_to_date", "Year To Date"),
            ("next_day", "Next Day"),
            ("next_week", "Next Week"),
            ("next_month", "Next Month"),
            ("next_quarter", "Next Quarter"),
            ("next_year", "Next Year"),
            ("last_day", "Last Day"),
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
            ("last_quarter", "Last Quarter"),
            ("last_year", "Last Year"),
            ("last_seven_days", "Last Seven Days"),
            ("last_thirty_days", "Last 30 Days"),
            ("last_ninety_days", "Last Ninety Days"),
            ("last_year_days", "Last 365 Days"),
            ("past_till_now", "Past Till Now"),
            ("past_excluding_today", "Past Excluding Today"),
            ("future_starting_today", "Future Starting Today"),
            ("future_starting_now", "Future Starting Now"),
            ("future_starting_tomorrow", "Future Starting Tomorrow"),
        ],
        default="none",
        string="Date Filter Options ",
        tracking=True,
    )
    kpi_include_periods = fields.Integer(string="Include Period ", default=0)
    kpi_same_period_previous_years = fields.Integer(
        string="Same Period Previous Years ", default=0
    )
    kpi_comparison_type = fields.Selection(
        [
            ("none", "None"),
            ("sum", "Sum"),
            ("ratio", "Ratio"),
            ("percentage", "Percentage"),
        ],
        default="none",
        string="Comparison Type",
        tracking=True,
    )
    kpi_enable_target = fields.Boolean(string="Enable Target")
    kpi_target_value = fields.Integer(string="Target Value", default=0)
    kpi_view_type = fields.Selection(
        [("standard", "Standard"), ("progress", "Progress")],
        default="standard",
        string="View",
    )

    # Main data fields
    model_id = fields.Many2one(
        "ir.model", string="Model", ondelete="set null", tracking=True
    )
    model = fields.Char(string="Model Ref.", related="model_id.model")
    measurement_field_ids = fields.Many2many(
        "ir.model.fields",
        "ir_fields_chart_rel",
        "chart_id",
        "field_id",
        string="Measurements",
        tracking=True,
    )

    list_type = fields.Selection(
        [("standard", "Standard"), ("grouped", "Grouped")],
        string="List Type",
        default="standard",
        help="Select group type.",
        tracking=True,
    )
    list_field_ids = fields.One2many(
        "list.fields",
        "field_id",
        string="List Standard Fields",
        copy=True,
        bypass_search_access=True,
        help="Select and add column fields for the standard list view.",
        tracking=True,
    )
    used_list_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Used List Ids",
        compute="_compute_used_list_fields",
        store=True,
    )
    list_measure_ids = fields.One2many(
        "list.fields",
        "measure_id",
        string="List Measure Fields",
        copy=True,
        bypass_search_access=True,
        help="Select and add column fields for the standard list view.",
    )

    todo_layout = fields.Selection(
        [
            ("default", "Default"),
            ("activity", "Activity"),
        ],
        default="default",
        string="To Do Layout",
        help="Select To Do action.",
        tracking=True,
    )
    todo_action_ids = fields.One2many(
        "todo.action",
        "layout_id",
        string="TODO Actions",
        copy=True,
        bypass_search_access=True,
        help="Set action for information purpose.",
    )

    image = fields.Binary(string="Image", help="Set image for mail")
    group_by_id = fields.Many2one(
        "ir.model.fields", string="Group By", ondelete="set null", tracking=True
    )
    group_by_type = fields.Selection(
        related="group_by_id.ttype", string="Group By Type", readonly=True
    )
    time_range = fields.Selection(
        [
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("quarter", "Quarter"),
            ("year", "Year"),
        ],
        string="Group by Time Range",
        help="Select time range on selected Group by Date option.",
    )

    map_group_by_id = fields.Many2one(
        "ir.model.fields", string="Map Group by", tracking=True
    )
    measurement_field_id = fields.Many2one(
        "ir.model.fields",
        string="Measure Field",
        tracking=True,
        ondelete="set null",
    )
    sub_group_by_id = fields.Many2one(
        "ir.model.fields",
        string="Sub Group By",
        tracking=True,
        ondelete="set null",
    )
    sub_group_by_type = fields.Selection(related="sub_group_by_id.ttype", readonly=True)
    sub_time_range = fields.Selection(
        [
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("quarter", "Quarter"),
            ("year", "Year"),
        ],
        string="Sub Group by Time Range",
        help="Select time range on selected Sub-Group by Date option.",
    )

    sort_field_id = fields.Many2one(
        "ir.model.fields",
        string="Sort With",
        tracking=True,
        ondelete="set null",
    )
    limit_record = fields.Integer(
        string="Record Limit",
        default=20,
        tracking=True,
        help="If you will change it to 0 (zero) then it will consider all records",
    )
    domain = fields.Char(string="Domain", default="[]")
    sort_order = fields.Selection(
        [("asc", "Ascending"), ("desc", "Descending")],
        string="Sort Order",
        default="asc",
        tracking=True,
    )
    data_type = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("average", "Average")],
        default="sum",
        string="Data Type",
        tracking=True,
    )
    background_color = fields.Char(string="Background Color", default="#fff")
    is_kpi_border = fields.Boolean(string="Enable Border")
    kpi_border_type = fields.Selection(
        [
            ("none", "None"),
            ("left", "Left"),
            ("right", "Right"),
            ("top", "Top"),
            ("bottom", "Bottom"),
        ],
        default="none",
        string="Border Type",
    )
    kpi_border_color = fields.Char(string="Border Color", default="#fff")
    kpi_border_width = fields.Integer(string="Border Width", default="10")
    font_color = fields.Char(string="Font Color", default="#000")
    layout_type = fields.Selection(
        [
            ("layout1", "Layout 1"),
            ("layout2", "Layout 2"),
            ("layout3", "Layout 3"),
            ("layout4", "Layout 4"),
            ("layout5", "Layout 5"),
        ],
        default="layout1",
        string="Layout",
        required=True,
    )
    tile_layout_type = fields.Selection(
        [
            ("layout1", "Layout 1"),
            ("layout2", "Layout 2"),
            ("layout3", "Layout 3"),
            ("layout4", "Layout 4"),
        ],
        default="layout1",
        string="Layout ",
        required=True,
    )
    text_align = fields.Selection(
        [("left", "Left"), ("center", "Center"), ("right", "Right")],
        string="Text Align",
        default="center",
    )
    theme = fields.Selection(
        [
            ("animated", "Animated"),
            ("frozen", "Frozen"),
            ("kelly", "Kelly"),
            ("material", "Material"),
            ("moonrise", "Moonrise"),
            ("spirited", "Spirited"),
        ],
        default="animated",
        string="Theme",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        related="dashboard_id.company_id",
        required=True,
    )
    item_view_action_ids = fields.One2many(
        "item.view.action", "chart_id", string="Item Actions"
    )
    item_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Last Item Action",
        tracking=True,
        ondelete="set null",
    )
    date_filter_field_id = fields.Many2one(
        "ir.model.fields",
        string="Date Filter Field",
        tracking=True,
        ondelete="set null",
    )
    date_filter_option = fields.Selection(
        [
            ("none", "None"),
            ("today", "Today"),
            ("this_week", "This Week"),
            ("this_month", "This Month"),
            ("this_quarter", "This Quarter"),
            ("this_year", "This Year"),
            ("week_to_date", "Week To Date"),
            ("month_to_date", "Month To Date"),
            ("quarter_to_date", "Quarter To Date"),
            ("year_to_date", "Year To Date"),
            ("next_day", "Next Day"),
            ("next_week", "Next Week"),
            ("next_month", "Next Month"),
            ("next_quarter", "Next Quarter"),
            ("next_year", "Next Year"),
            ("last_day", "Last Day"),
            ("last_week", "Last Week"),
            ("last_month", "Last Month"),
            ("last_quarter", "Last Quarter"),
            ("last_year", "Last Year"),
            ("last_seven_days", "Last Seven Days"),
            ("last_thirty_days", "Last 30 Days"),
            ("last_ninety_days", "Last Ninety Days"),
            ("last_year_days", "Last 365 Days"),
            ("past_till_now", "Past Till Now"),
            ("past_excluding_today", "Past Excluding Today"),
            ("future_starting_today", "Future Starting Today"),
            ("future_starting_now", "Future Starting Now"),
            ("future_starting_tomorrow", "Future Starting Tomorrow"),
        ],
        default="none",
        string="Date Filter Options",
        tracking=True,
    )
    is_apply_multiplier = fields.Boolean(
        string="Apply Multiplier", default=False, tracking=True
    )
    chart_multiplier_ids = fields.One2many(
        "chart.multiplier", "chart_id", string="Chart Multiplier"
    )
    include_periods = fields.Integer(string="Include Period", default=0)
    same_period_previous_years = fields.Integer(
        string="Same Period Previous Years", default=0
    )
    icon_option = fields.Selection(
        [("default", "Default"), ("custom", "Custom")],
        default="default",
        string="Icon Option",
    )
    default_icon = fields.Char(string="Default Icon")
    icon = fields.Binary(string="Icon ")
    previous_period_comparision = fields.Boolean(
        string="Previous Period Comparison",
        help="Activate/deactivate previous comparison in KPI layout.",
        tracking=True,
    )
    previous_period_duration = fields.Integer(
        string="Previous Period Duration",
        default=1,
        tracking=True,
        help="Set the value integer to be compared with the configured date filter for the KPI layout. \n For e.g. In date filter it is set to 'This Year' and if you set the value to 2 then 'This year' records will be compared with 2 years back previous records",
    )
    previous_period_type = fields.Selection(
        [("percentage", "Percentage"), ("value", "Value")],
        string="Previous Period Type",
        default="percentage",
        tracking=True,
    )
    show_unit = fields.Boolean("Show Unit", help="Set unit type on axis.")
    unit_type = fields.Selection(
        [("monetary", "Monetary"), ("custom", "Custom")],
        string="Unit Type",
        default="monetary",
        help="Select unit type for axis.",
    )
    custom_unit = fields.Char("Custom Unit", help="Set custom unit type on 'Y' axis.")
    group_ids = fields.Many2many(
        "res.groups",
        "chart_group_rel",
        "chart_id",
        "group_id",
        string="Access Groups",
    )

    button_color = fields.Char(string="Top Button Color")
    font_size = fields.Integer(
        string="Font Size", help="Set font size for Tile", default=35
    )
    font_weight = fields.Selection(
        [
            ("100", "100"),
            ("200", "200"),
            ("300", "300"),
            ("400", "400"),
            ("500", "500"),
            ("600", "600"),
            ("700", "700"),
            ("800", "800"),
            ("900", "900"),
        ],
        string="Font Weight",
        help="Set font thickness for Tile",
        default="600",
    )
    hide_false_value = fields.Boolean(string="Hide False", default=True)

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        """
        Override method to filter chars for dashboard email
        """
        domain = list(domain or [])
        context = dict(self.env.context)
        if context.get("is_automated"):
            domain_list = [("chart_type", "in", ["kpi", "tile", "list", "to_do"])]
            domain = fields.Domain.AND([domain_list, domain])
        return super(DashboardChart, self).name_search(
            name=name, domain=domain, operator=operator, limit=limit
        )

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = list(domain or [])
        context = dict(self.env.context)
        if context.get("is_automated"):
            args = [("chart_type", "in", ["kpi", "tile", "list", "to_do"])]
            domain = fields.Domain.AND([args, domain])
        return super(DashboardChart, self).search_fetch(
            domain=domain,
            field_names=field_names,
            offset=offset,
            limit=limit,
            order=order,
        )

    @api.constrains("limit_record")
    def _check_limit_record(self):
        for chart in self:
            if chart.limit_record and chart.limit_record < 0:
                raise ValidationError(
                    _(
                        "Oops! The record limit can’t be less than zero. Please enter a value of zero or higher to continue."
                    )
                )

    @api.onchange("include_periods", "same_period_previous_years")
    def onchange_periods(self):
        if self.include_periods < 0:
            self.include_periods = 0
        if self.same_period_previous_years < 0:
            self.same_period_previous_years = 0

    @api.onchange("todo_layout")
    def onchange_todo_layout(self):
        """
        Set model as a False base on ToDo layout
        """
        if self.todo_layout == "default":
            self.model_id = False

    @api.onchange("date_filter_option")
    def onchange_date_filter_option(self):
        """
        Set periods
        """
        if self.date_filter_option in [
            "none",
            "past_till_now",
            "past_excluding_today",
            "future_starting_today",
            "future_starting_now",
            "future_starting_tomorrow",
        ]:
            self.include_periods = 0
            self.same_period_previous_years = 0

    @api.onchange("model_id")
    def onchange_model_id(self):
        """
        To set date filter field
        """
        self.measurement_field_ids = [(5,)]
        self.group_by_id = False
        self.measurement_field_id = False
        self.sub_group_by_id = False
        self.is_apply_multiplier = False
        self.map_group_by_id = False
        self.domain = "[]"
        self.date_filter_field_id = False
        self.sort_field_id = False
        self.list_field_ids = False
        self.item_view_action_ids = [(5,)]
        self.item_action_id = False
        self.list_measure_ids = False
        if self.model_id:
            field_id = (
                self.env["ir.model.fields"]
                .sudo()
                .search(
                    [("name", "=", "create_date"), ("model_id", "=", self.model_id.id)]
                )
            )
            self.date_filter_field_id = field_id.id
        self.onchange_apply_multiplier()

    @api.onchange("kpi_model_id")
    def onchange_kpi_model_id(self):
        """
        To set KPI date filter field
        """
        self.kpi_measurement_field_id = False
        self.kpi_data_type = "count"
        self.kpi_domain = "[]"
        self.kpi_comparison_type = "none"
        self.kpi_date_filter_option = "none"
        self.kpi_date_filter_field_id = False
        if self.kpi_model_id:
            field_id = (
                self.env["ir.model.fields"]
                .sudo()
                .search(
                    [
                        ("name", "=", "create_date"),
                        ("model_id", "=", self.kpi_model_id.id),
                    ]
                )
            )
            self.kpi_date_filter_field_id = field_id.id
        self.onchange_apply_multiplier()

    @api.onchange("measurement_field_id", "measurement_field_ids")
    def onchange_measurement_field(self):
        self.onchange_apply_multiplier()

    @api.onchange("is_apply_multiplier")
    def onchange_apply_multiplier(self):
        """
        Set chart multipliers
        """
        multiplier_list = [(5,)]
        if self.is_apply_multiplier:
            for measurement in self.measurement_field_ids:
                multiplier_list.append((0, 0, {"field_id": measurement.id}))
            if self.measurement_field_id:
                multiplier_list.append(
                    (0, 0, {"field_id": self.measurement_field_id.id})
                )
        self.chart_multiplier_ids = multiplier_list

    @api.onchange("chart_type")
    def onchange_chart_type(self):
        """
        Change model
        """
        # self.model_id = False
        self.background_color = "#fff"
        # self.onchange_model_id()
        chart_properties = {
            "tile": [
                "data_type",
                "measurement_field_id",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "kpi": [
                "data_type",
                "measurement_field_id",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "kpi_model_id",
                "kpi_data_type",
                "kpi_measurement_field_id",
                "kpi_limit_record",
                "kpi_comparison_type",
                "kpi_domain",
                "kpi_enable_target",
                "kpi_target_value",
                "kpi_view_type",
                "kpi_date_filter_field_id",
                "kpi_date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "previous_period_comparision",
                "previous_period_type",
            ],
            "bar_chart": [
                "data_type",
                "measurement_field_ids",
                "group_by_id",
                "time_range",
                "sub_group_by_id",
                "sub_time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "funnel_chart": [
                "data_type",
                "measurement_field_id",
                "group_by_id",
                "time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "pyramid_chart": [
                "data_type",
                "measurement_field_id",
                "group_by_id",
                "time_range",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "map_chart": [
                "data_type",
                "measurement_field_id",
                "map_group_by_id",
                "hide_false_value",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
            "meter_chart": [
                "data_type",
                "measurement_field_id",
                "meter_target",
                "domain",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
                "previous_period_comparision",
                "previous_period_type",
            ],
            "to_do": [
                "todo_layout",
                "todo_action_ids",
                "domain",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
            ],
            "list": [
                "list_type",
                "list_field_ids",
                "domain",
                "sort_field_id",
                "sort_order",
                "limit_record",
                "date_filter_field_id",
                "date_filter_option",
                "include_periods",
                "same_period_previous_years",
            ],
        }

        if self.chart_type in [
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "area_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        ]:
            chart_type = "bar_chart"
        elif self.chart_type in [
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
        ]:
            chart_type = "funnel_chart"
        else:
            chart_type = self.chart_type

        allowed_fields = set(chart_properties.get(chart_type or "", []))
        all_fields = set(
            field for fields in chart_properties.values() for field in fields
        )

        for field in all_fields:
            if field not in allowed_fields:
                try:
                    if field in [
                        "measurement_field_ids",
                        "todo_action_ids",
                        "list_field_ids",
                    ]:
                        setattr(self, field, [(5,)])
                    elif field in ["domain", "kpi_domain"]:
                        setattr(self, field, "[]")
                    elif field in ["kpi_date_filter_option", "date_filter_option"]:
                        setattr(self, field, "none")
                    else:
                        setattr(self, field, False)
                except Exception:
                    _logger.info("pass")
        if self.chart_type == "to_do":
            self.todo_layout = "default"
        elif self.chart_type == "list":
            self.list_type = "standard"
        else:
            self.todo_layout = False
            self.list_type = False
            if not self.data_type:
                self.data_type = "count"

    def export_csv(self, name, chart_type, print_vals=False):
        """
        Export data in CSV file type for charts
        """
        print_options = False
        if print_vals.get("breadcrump_ids"):
            print_options = {
                "breadcrump_ids": print_vals.get("breadcrump_ids")[-1:],
                "domain": print_vals.get("prev_domains"),
            }
        data = self.get_chart_data(chart_type, name, print_options=print_options)
        if isinstance(data, dict) and data.get("type") == "error":
            return {"error": True}
        output = io.StringIO()
        writer = csv.writer(output)
        if chart_type in [
            "area_chart",
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        ]:
            all_metrics = set()
            normalized_rows = []

            for entry in data:
                category = entry.get("category")
                group_data = defaultdict(dict)
                for key, value in entry.items():
                    if key in ["category", "record_id"]:
                        continue
                    if " - " in key:
                        group_name, metric = key.rsplit(" - ", 1)
                    else:
                        group_name = key
                        metric = "Value"
                    group_data[group_name][metric] = value
                    all_metrics.add(metric)
                normalized_rows.extend(
                    [
                        {"Category": category, "Name": group_name, **metrics}
                        for group_name, metrics in group_data.items()
                    ]
                )
            metric_list = sorted(all_metrics)

            writer = csv.DictWriter(
                output, fieldnames=["Category", "Name"] + metric_list
            )
            writer.writeheader()
            for row in normalized_rows:
                writer.writerow(row)
        elif chart_type in [
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
            "map_chart",
        ]:
            if chart_type == "map_chart":
                writer.writerow(["Name", "Value"])  # Header
            else:
                writer.writerow(["Category", "Value"])  # Header
            for row in data:
                if chart_type == "map_chart":
                    writer.writerow([row["name"], row["value"]])
                else:
                    writer.writerow([row["category"], row["value"]])
        elif chart_type == "list":
            column_lists = list(map(lambda col: col.get("name"), data["columns"]))
            writer.writerow(column_lists)
            for record in data["records"]:
                row_list = []
                for col in data["columns"]:
                    row_list.append(record.get(col["column_name"]))
                writer.writerow(row_list)

        elif chart_type == "to_do":
            if self.todo_layout == "default":
                writer.writerow(["Name", "Task"])
                for record in data["records"]:
                    for action in record.get("action_line_ids"):
                        if action.get("active_record"):
                            writer.writerow([record.get("name"), action.get("name")])
            else:
                writer.writerow(["Date", "Summary", "Name", "User", "Activity Type"])

                for record in data["records"]:
                    writer.writerow(
                        [
                            record["date"].strftime("%Y-%m-%d"),
                            record["summary"] if record["summary"] else "",
                            record["name"],
                            record["username"],
                            record["activity_type"],
                        ]
                    )

        file_name = name + ".csv"
        csv_bytes = output.getvalue().encode("utf-8")
        base64_content = base64.b64encode(csv_bytes).decode("utf-8")
        return {"file_content": base64_content, "file_name": file_name}

    def export_excel(self, name, chart_type, print_vals=False):
        """
        Export data in Excel file type for charts
        """

        def set_column_widths(worksheet, col_widths):
            """
            Set width of the column
            """
            for col, width in col_widths.items():
                worksheet.set_column(col, col, width + 2)

        def write_headers(worksheet, row, col, headers, header_format):
            """
            Set header values
            """
            for i, header in enumerate(headers):
                worksheet.write(row, col + i, header, header_format)

        def write_data_block(
            worksheet,
            start_row,
            start_col,
            base_keys,
            labels,
            category,
            header_fmt,
            cell_fmt,
        ):
            """
            Set date into blocks
            """
            worksheet.merge_range(
                start_row,
                start_col,
                start_row,
                start_col + len(labels),
                category,
                header_fmt,
            )
            worksheet.write(start_row + 1, start_col, "Name", cell_fmt)
            for j, label in enumerate(labels):
                worksheet.write(start_row + 1, start_col + 1 + j, label, cell_fmt)
            for i, (base, metrics) in enumerate(base_keys.items()):
                row = start_row + 2 + i
                worksheet.write(row, start_col, base, cell_fmt)
                for j, label in enumerate(labels):
                    worksheet.write(
                        row, start_col + 1 + j, metrics.get(label, ""), cell_fmt
                    )

        def get_max_col_widths(data, labels, base_keys, start_col):
            """
            Calculate column width
            """
            col_widths = {}
            col_widths[start_col] = max(len(k) for k in base_keys.keys())
            for j, label in enumerate(labels):
                col = start_col + 1 + j
                col_widths[col] = len(label)
                for metrics in base_keys.values():
                    col_widths[col] = max(
                        col_widths[col], len(str(metrics.get(label, "")))
                    )
            return col_widths

        print_options = False
        if print_vals.get("breadcrump_ids"):
            print_options = {
                "breadcrump_ids": print_vals.get("breadcrump_ids")[-1:],
                "domain": print_vals.get("prev_domains"),
            }
        data = self.get_chart_data(chart_type, name, print_options=print_options)
        if isinstance(data, dict) and data.get("type") == "error":
            return {"error": True}
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(name)

        blocks_per_row, col_gap, row_gap = 3, 3, 3
        col_widths = {}

        if chart_type in {
            "area_chart",
            "bar_chart",
            "column_chart",
            "doughnut_chart",
            "line_chart",
            "stackedcolumn_chart",
            "radial_chart",
            "scatter_chart",
        }:
            for index, entry in enumerate(data):
                category = entry.get("category")
                base_keys = {}
                for key, value in entry.items():
                    if key not in ["category", "record_id"]:
                        if " - " in key and len(key.split(" - ")) > 1:
                            base, label = key.rsplit(" - ", 1)
                            base_keys.setdefault(base, {})[label] = value
                        else:
                            base_keys.setdefault("Count", {})[key] = value
                if not base_keys:
                    continue
                labels = sorted(
                    {label for metrics in base_keys.values() for label in metrics}
                )
                block_x = (index % blocks_per_row) * (len(labels) + 1 + col_gap)
                block_y = (index // blocks_per_row) * (len(base_keys) + 2 + row_gap)
                write_data_block(
                    worksheet,
                    block_y,
                    block_x,
                    base_keys,
                    labels,
                    category,
                    workbook.add_format(
                        {
                            "bold": True,
                            "align": "center",
                            "valign": "vcenter",
                            "border": 1,
                            "bg_color": "#D9E1F2",
                        }
                    ),
                    workbook.add_format({"bold": True, "border": 1}),
                )
                col_widths.update(get_max_col_widths(data, labels, base_keys, block_x))
            set_column_widths(worksheet, col_widths)

        elif chart_type in {
            "funnel_chart",
            "pyramid_chart",
            "pie_chart",
            "radar_chart",
            "map_chart",
        }:
            for index, entry in enumerate(data):
                category = (
                    entry.get("category")
                    if chart_type != "map_chart"
                    else entry.get("name")
                )
                value = entry.get("value", "")
                block_x = (index % blocks_per_row) * (3 + col_gap)
                block_y = (index // blocks_per_row) * (3 + row_gap)

                worksheet.merge_range(
                    block_y,
                    block_x,
                    block_y,
                    block_x + 1,
                    category,
                    workbook.add_format(
                        {
                            "bold": True,
                            "align": "center",
                            "valign": "vcenter",
                            "border": 1,
                            "bg_color": "#F4B084",
                        }
                    ),
                )
                worksheet.write(
                    block_y + 1,
                    block_x,
                    "Value",
                    workbook.add_format({"bold": True, "border": 1}),
                )
                worksheet.write(
                    block_y + 1, block_x + 1, value, workbook.add_format({"border": 1})
                )
                col_widths[block_x] = max(
                    col_widths.get(block_x, 0), len(category) if category else 5
                )
                col_widths[block_x + 1] = max(
                    col_widths.get(block_x + 1, 0), len(str(value))
                )
            set_column_widths(worksheet, col_widths)

        elif chart_type == "list":
            columns = data["columns"]
            records = data["records"]

            column_order = [col["column_name"] for col in columns]
            column_headers = [col["name"] for col in columns]
            write_headers(
                worksheet,
                0,
                0,
                column_headers,
                workbook.add_format({"bold": True, "bg_color": "#BDD7EE", "border": 1}),
            )
            for row_idx, record in enumerate(records, start=1):
                for col_idx, key in enumerate(column_order):
                    worksheet.write(
                        row_idx,
                        col_idx,
                        record.get(key, ""),
                        workbook.add_format({"border": 1}),
                    )
            for col_idx, key in enumerate(column_order):
                max_width = max(len(str(record.get(key, ""))) for record in records)
                header_width = len(column_headers[col_idx])
                worksheet.set_column(col_idx, col_idx, max(max_width, header_width) + 2)

        elif chart_type == "to_do":
            if self.todo_layout == "default":
                records = data["records"]
                columns_data = {
                    record["name"]: [
                        line["name"]
                        for line in record.get("action_line_ids", [])
                        if line.get("active_record")
                    ]
                    for record in records
                }
                write_headers(
                    worksheet,
                    0,
                    0,
                    list(columns_data.keys()),
                    workbook.add_format(
                        {
                            "bold": True,
                            "bg_color": "#D9E1F2",
                            "border": 1,
                            "align": "center",
                        }
                    ),
                )
                for col_idx, (col_name, lines) in enumerate(columns_data.items()):
                    for row_idx, value in enumerate(lines, start=1):
                        worksheet.write(
                            row_idx, col_idx, value, workbook.add_format({"border": 1})
                        )
                    max_width = max([len(str(v)) for v in lines], default=0)
                    worksheet.set_column(
                        col_idx, col_idx, max(max_width, len(col_name)) + 2
                    )

            else:
                records = data.get("records", [])
                headers = ["Date", "Summary", "Name", "User", "Activity Type"]
                keys = ["date", "summary", "name", "username", "activity_type"]
                write_headers(
                    worksheet,
                    0,
                    0,
                    headers,
                    workbook.add_format(
                        {
                            "bold": True,
                            "bg_color": "#B7DEE8",
                            "border": 1,
                            "align": "center",
                        }
                    ),
                )
                date_fmt = workbook.add_format(
                    {"num_format": "dd-mm-yyyy", "border": 1}
                )
                text_fmt = workbook.add_format({"border": 1})
                for row_idx, record in enumerate(records, start=1):
                    for col_idx, key in enumerate(keys):
                        val = record.get(key, "")
                        if key == "date" and val:
                            worksheet.write_datetime(row_idx, col_idx, val, date_fmt)
                        else:
                            worksheet.write(
                                row_idx,
                                col_idx,
                                val if val is not False else "",
                                text_fmt,
                            )
                for col_idx, key in enumerate(keys):
                    max_width = max(len(str(record.get(key, ""))) for record in records)
                    worksheet.set_column(
                        col_idx, col_idx, max(max_width, len(headers[col_idx])) + 2
                    )

        workbook.close()
        output.seek(0)
        return {
            "file_content": base64.b64encode(output.read()).decode("utf-8"),
            "file_name": f"{name}.xlsx",
        }

    def evaluate_odoo_domain(self, domain_string):
        class OdooSafeDatetime:
            def __init__(self, dt):
                self._dt = dt

            def to_utc(self):
                utc_dt = fields.Datetime.to_datetime(self._dt)
                return OdooSafeDatetime(utc_dt)

            def strftime(self, fmt):
                return self._dt.strftime(fmt)

        class OdooDatetimeClass:
            @staticmethod
            def combine(date_obj, time_obj):
                combined = datetime.combine(date_obj, time_obj)
                return OdooSafeDatetime(combined)

        class DatetimeModule:
            datetime = OdooDatetimeClass
            time = time

        def get_context_today():
            return fields.Datetime.context_timestamp(self, datetime.now()).date()

        eval_context = {
            "datetime": DatetimeModule(),
            "context_today": get_context_today,
            "relativedelta": relativedelta,
        }

        try:
            return safe_eval(domain_string, eval_context)
        except Exception as e:
            _logger.warning(f"Failed to evaluate domain: {domain_string}, Error: {e}")
            return []

    def get_chart_data(
        self,
        chart_type,
        name,
        isDirty=False,
        data=False,
        extra_action=False,
        print_options=False,
    ):
        """
        this function is called from chart wrapper and form preview.
        In case of any field get changed in form view then this function will
        make sure it will preview based on latest changes of configuration,
        also In case of there is item action and item views are linked to charts then in
        each click on chart this function will redirect action or replace current chart
        """
        conf, domain = self._init_configuration()
        if isDirty:
            self._handle_dirty_data(conf, data)
        conf.chart_type = chart_type
        if print_options:
            domain = print_options.get("domain")
            view_item = self.env["item.view.action"].browse(
                print_options.get("breadcrump_ids")
            )
            if view_item:
                chart_type = view_item.chart_type
                conf.domain = domain
                if not conf.measurement_field_id and conf.measurement_field_ids:
                    conf.measurement_field_id = conf.measurement_field_ids[0]
                if not conf.measurement_field_ids:
                    conf.measurement_field_ids = conf.measurement_field_id
                conf.group_by = view_item.group_by_id.name
                conf.sort_field = view_item.sort_field_id.name
                conf.sort_order = view_item.sort_order
                conf.limit_record = view_item.limit_record
        else:
            domain = self._process_domain(domain, extra_action, self.group_by_id)
            view_item = self._get_view_item(extra_action)
            if view_item:
                chart_type = view_item.chart_type
                conf.domain = domain
                if not conf.measurement_field_id and conf.measurement_field_ids:
                    conf.measurement_field_id = conf.measurement_field_ids[0]
                if not conf.measurement_field_ids:
                    conf.measurement_field_ids = conf.measurement_field_id
                conf.group_by = view_item.group_by_id.name
                conf.sort_field = view_item.sort_field_id.name
                conf.sort_order = view_item.sort_order
                conf.limit_record = view_item.limit_record
        chart_handlers = {
            "area_chart": self.get_measurement_group_data,
            "bar_chart": self.get_measurement_group_data,
            "column_chart": self.get_measurement_group_data,
            "doughnut_chart": self.get_measurement_group_data,
            "line_chart": self.get_measurement_group_data,
            "stackedcolumn_chart": self.get_measurement_group_data,
            "radial_chart": self.get_measurement_group_data,
            "scatter_chart": self.get_measurement_group_data,
            "funnel_chart": self.get_category_value_data,
            "pyramid_chart": self.get_category_value_data,
            "pie_chart": self.get_category_value_data,
            "radar_chart": self.get_category_value_data,
            "map_chart": self.get_map_chart_data,
            "meter_chart": self.get_meter_chart_data,
            "list": self.get_list_view_data,
            "tile": self.get_tile_data,
            "kpi": self.get_kpi_data,
            "to_do": self.get_todo_data,
        }
        prepared_data = chart_handlers.get(chart_type, lambda x: [])(conf)
        return self._build_final_response(
            prepared_data, domain, chart_type, view_item, extra_action
        )

    def _init_configuration(self):
        """
        Configure global cong variable
        """
        conf = SimpleNamespace(
            model=self.model_id.model,
            name=self.name,
            hide_false_value=self.hide_false_value,
            show_unit=self.show_unit,
            unit_type=self.unit_type,
            custom_unit=self.custom_unit,
            layout_type=self.layout_type,
            tile_layout_type=self.tile_layout_type,
            meter_target=self.meter_target,
            text_align=self.text_align,
            background_color=self.background_color,
            is_kpi_border=self.is_kpi_border,
            kpi_border_type=self.kpi_border_type,
            kpi_border_color=self.kpi_border_color,
            kpi_border_width=self.kpi_border_width,
            font_color=self.font_color,
            font_size=self.font_size,
            font_weight=self.font_weight,
            group_by=self.group_by_id.name,
            time_range=self.time_range,
            map_group_by=self.map_group_by_id.name,
            sub_group_by=self.sub_group_by_id.name,
            sub_time_range=self.sub_time_range,
            measurement_field_ids=self.measurement_field_ids,
            sort_field=self.sort_field_id.name,
            sort_order=self.sort_order,
            limit_record=self.limit_record,
            date_filter_field=self.date_filter_field_id.name,
            date_filter_option=self.date_filter_option,
            domain=self.evaluate_odoo_domain(self.domain) if self.domain else [],
            data_type=self.data_type,
            company=self.company_id.id,
            measurement_field_id=self.measurement_field_id,
            include_periods=self.include_periods,
            same_period_previous_years=self.same_period_previous_years,
            list_type=self.list_type,
            icon_option=self.icon_option,
            default_icon=self.default_icon,
            icon=self.icon,
            kpi_model=self.kpi_model_id.model,
            kpi_data_type=self.kpi_data_type,
            kpi_measurement_field_id=self.kpi_measurement_field_id,
            kpi_limit_record=self.kpi_limit_record,
            kpi_domain=self.evaluate_odoo_domain(self.kpi_domain)
            if self.kpi_domain
            else [],
            kpi_date_filter_field_id=self.kpi_date_filter_field_id.name,
            kpi_date_filter_option=self.kpi_date_filter_option,
            kpi_include_periods=self.kpi_include_periods,
            kpi_same_period_previous_years=self.kpi_same_period_previous_years,
            kpi_comparison_type=self.kpi_comparison_type,
            kpi_enable_target=self.kpi_enable_target,
            kpi_target_value=self.kpi_target_value,
            kpi_view_type=self.kpi_view_type,
            previous_period_comparision=self.previous_period_comparision,
            previous_period_duration=self.previous_period_duration,
            previous_period_type=self.previous_period_type,
            is_apply_multiplier=self.is_apply_multiplier,
            todo_layout=self.todo_layout,
            todo_action_ids=[
                {
                    "name": action.name,
                    "action_line_ids": [
                        {
                            "name": action_line.name,
                            "active_record": action_line.active_record,
                        }
                        for action_line in action.action_line_ids
                    ],
                }
                for action in self.todo_action_ids
            ],
            chart_multiplier_ids=[
                {"field_id": m.field_id.id, "multiplier": m.multiplier}
                for m in self.chart_multiplier_ids
            ],
            list_measure_ids=[
                {"list_measure_id": m.list_measure_id.id, "value_type": m.value_type}
                for m in self.list_measure_ids
            ],
            list_field_ids=[
                {"list_field_id": f.list_field_id.id, "sequence": f.sequence}
                for f in self.list_field_ids
            ],
        )
        return conf, conf.domain.copy()

    def html_to_image(self):
        chart_data = self.get_chart_data(self.chart_type, self.name)
        recordsets = {
            "chart_id": self.id,
            "chart_type": self.chart_type,
            "name": self.name,
        }
        if "default_icon" in chart_data and chart_data.get("default_icon"):
            chart_data.update({"kpi_icon": Markup(chart_data.get("default_icon"))})
        recordsets.update(chart_data)
        height = "300px"
        style = "margin: 0; padding: 20px;"
        template_html = ""
        if self.chart_type == "list":
            style = "margin: 0; padding: 0;"
            records = recordsets.get("records")
            if records is None:
                image_height = 500
            else:
                image_height = 200
                if len(records) > 5:
                    image_height = 280 * (len(records) / 6)
                    if image_height < 280:
                        image_height = 280
                elif len(records) <= 2:
                    image_height = 150
            if image_height > 6000:
                recordsets.update(
                    {
                        "isError": True,
                        "errorMessage": "Such large image can not be added!",
                    }
                )
                image_height = 300
            height = "%spx" % int(image_height)

            template_html = self.env["ir.ui.view"]._render_template(
                "synconics_bi_dashboard.list_layout", {"recordsets": recordsets}
            )
            template_html = f"""<div class="col-sm-12 col-md-12 oe_inner">
                                                            {template_html}
                                                        </div>"""
        elif self.chart_type == "to_do":
            template_html = ""
            if recordsets.get("layout_type") == "activity":
                style = "margin: 0; padding: 0;"
                records = recordsets.get("records")
                image_height = 200
                if len(records) > 5:
                    image_height = 280 * (len(records) / 10)
                elif len(records) <= 2:
                    image_height = 150
                if image_height > 6000:
                    recordsets.update(
                        {
                            "isError": True,
                            "errorMessage": "Such large image can not be added!",
                        }
                    )
                    image_height = 300
                height = "%spx" % image_height

                template_html = self.env["ir.ui.view"]._render_template(
                    "synconics_bi_dashboard.to_do_layout", {"recordsets": recordsets}
                )
                template_html = f"""<div class="col-sm-12 col-md-12 oe_inner">
                                                                {template_html}
                                                            </div>"""
        else:
            kpi_layout_options = {
                "layout1": "synconics_bi_dashboard.kpi_layout_one",
                "layout2": "synconics_bi_dashboard.kpi_layout_two",
                "layout3": "synconics_bi_dashboard.kpi_layout_three",
                "layout4": "synconics_bi_dashboard.kpi_layout_four",
                "layout5": "synconics_bi_dashboard.kpi_layout_five",
            }
            tile_layout_options = {
                "layout1": "synconics_bi_dashboard.tile_layout_one",
                "layout2": "synconics_bi_dashboard.tile_layout_two",
                "layout3": "synconics_bi_dashboard.tile_layout_three",
                "layout4": "synconics_bi_dashboard.tile_layout_four",
            }
            if self.chart_type == "kpi":
                if "type" in recordsets and recordsets.get("type") == "error":
                    template_html = ""
                else:
                    template_html = self.env["ir.ui.view"]._render_template(
                        kpi_layout_options.get(self.layout_type),
                        {"recordsets": recordsets},
                    )
            else:
                if "type" in recordsets and recordsets.get("type") == "error":
                    template_html = ""
                else:
                    template_html = self.env["ir.ui.view"]._render_template(
                        tile_layout_options.get(self.tile_layout_type),
                        {"recordsets": recordsets},
                    )
            template_html = f"""<div class="col-sm-12 col-md-12 oe_inner" style="height: 89%">
                                                            {template_html}
                                                        </div>"""
        alignment_fix_css = """
            <style>
                /* Fix for imgkit flexbox alignment issues */
                .row.d-flex[style*="align-items: center"] {
                    display: table !important;
                    width: 100% !important;
                    height: 100% !important;
                }
                .row.d-flex[style*="align-items: center"] > .col-md-12,
                .row[style*="align-items"] > .col-md-12 {
                    display: table-cell !important;
                    vertical-align: middle !important;
                }

                /* Preserve text alignment */
                [style*="text-align:center"] {
                    text-align: center !important;
                }

                /* Force table layout for bottom sections */
                .o_bottom {
                    display: table !important;
                    width: 100% !important;
                    table-layout: fixed !important;
                    position: absolute;
                    bottom: 4px;
                    left: 0;
                    right: 0;
                }

                .oe_target, .oe_prev {
                    display: table-cell !important;
                    vertical-align: bottom !important;
                    width: 50% !important;
                }
                .oe_target { text-align: left !important; }
                .oe_prev { text-align: right !important; }

                /* Ensure proper spacing and alignment */
                .metric-container {
                    display: inline-block !important;
                    margin-bottom: 2px !important;
                }
            </style>
        """
        if self.layout_type == "layout1":
            alignment_fix_css = alignment_fix_css.replace(
                "</style>",
                """
                .fa-bullseye, .fa-calendar {
                    background-color: #cecece61;
                    height: auto;
                    padding: 5px;
                    size: a3;
                    font-size: 18px;
                }
                </style>
                """,
            )

        full_html = f"""
        <html>
            <head>
                <meta charset="utf-8">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
                {alignment_fix_css}
                <style>
                    body {{ {style} }}
                </style>
            </head>
            <body style="height: {height}; width: 100%;">
                {template_html}
            </body>
        </html>
        """

        options = {
            "encoding": "UTF-8",
            "zoom": "1",
        }
        img_binary = imgkit.from_string(full_html, False, options=options)
        img_base64 = base64.b64encode(img_binary).decode("UTF-8")
        img_data_url = f"data:image/jpeg;base64,{img_base64}"
        return img_data_url

    def _handle_dirty_data(self, conf, data):
        """
        Apply logic base on Dirty data variable
        """
        ir_model = self.env["ir.model"].sudo()
        ir_model_fields = self.env["ir.model.fields"].sudo()

        update_conf_dict = {
            "hide_false_value": data.get("hide_false_value"),
            "show_unit": data.get("show_unit"),
            "unit_type": data.get("unit_type"),
            "tile_layout_type": data.get("tile_layout_type", "layout1"),
            "custom_unit": data.get("custom_unit"),
            "model": ir_model.browse(data.get("model_id")).model
            if "model_id" in data
            else None,
            "domain": self.evaluate_odoo_domain(data.get("domain"))
            if "domain" in data
            else [],
            "group_by": ir_model_fields.browse(data.get("group_by_id")).name
            if "group_by_id" in data
            else None,
            "time_range": data.get("time_range"),
            "map_group_by": ir_model_fields.browse(data.get("map_group_by_id")).name
            if "map_group_by_id" in data
            else None,
            "meter_target": data.get("meter_target"),
            "font_size": data.get("font_size"),
            "font_weight": data.get("font_weight"),
            "date_filter_field": ir_model_fields.browse(
                data.get("date_filter_field_id")
            ).name
            if "date_filter_field_id" in data
            else None,
            "sub_group_by": ir_model_fields.browse(data.get("sub_group_by_id")).name
            if "sub_group_by_id" in data
            else None,
            "sub_time_range": data.get("sub_time_range"),
            "measurement_field_ids": ir_model_fields.browse(
                data.get("measurement_field_ids", [])
            ),
            "sort_field": ir_model_fields.browse(data.get("sort_field_id")).name
            if "sort_field_id" in data
            else None,
            "todo_layout": data.get("todo_layout", "default"),
            "todo_action_ids": data.get("todo_action_ids", []),
            "list_type": data.get("list_type", "standard"),
            "list_measure_ids": data.get("list_measure_ids", []),
            "list_field_ids": data.get("list_field_ids", []),
            "include_periods": data.get("include_periods", 0),
            "same_period_previous_years": data.get("same_period_previous_years", 0),
            "date_filter_option": data.get("date_filter_option"),
            "measurement_field_id": ir_model_fields.browse(data["measurement_field_id"])
            if isinstance(data.get("measurement_field_id"), int)
            else data.get("measurement_field_id"),
            "is_apply_multiplier": data.get("is_apply_multiplier", False),
            "chart_multiplier_ids": data.get("chart_multiplier_ids", []),
            "company": data.get("company_id"),
            "data_type": data.get("data_type", "sum"),
            "limit_record": data.get("limit_record") or 0,
            "sort_order": data.get("sort_order"),
            "name": data.get("name", ""),
            "layout_type": data.get("layout_type", "layout1"),
            "text_align": data.get("text_align", "center"),
            "background_color": data.get("background_color", "#CCC"),
            "is_kpi_border": data.get("is_kpi_border", False),
            "kpi_border_type": data.get("kpi_border_type"),
            "kpi_border_color": data.get("kpi_border_color"),
            "kpi_border_width": data.get("kpi_border_width"),
            "font_color": data.get("font_color", "#FFF"),
            "icon_option": data.get("icon_option", False),
            "default_icon": data.get("default_icon", ""),
            "icon": data.get("icon", b""),
            "kpi_model": ir_model.browse(data.get("kpi_model_id")).model
            if "kpi_model_id" in data
            else None,
            "kpi_data_type": data.get("kpi_data_type", "sum"),
            "kpi_measurement_field_id": ir_model_fields.browse(
                data["kpi_measurement_field_id"]
            )
            if isinstance(data.get("kpi_measurement_field_id"), int)
            else data.get("kpi_measurement_field_id"),
            "kpi_limit_record": data.get("kpi_limit_record") or 0,
            "kpi_domain": self.evaluate_odoo_domain(data.get("kpi_domain"))
            if "kpi_domain" in data
            else [],
            "kpi_data_filter_field_id": ir_model_fields.browse(
                data["kpi_data_filter_field_id"]
            )
            if isinstance(data.get("kpi_data_filter_field_id"), int)
            else data.get("kpi_data_filter_field_id"),
            "kpi_date_filter_option": data.get("kpi_date_filter_option"),
            "kpi_include_periods": data.get("kpi_include_periods", 0),
            "kpi_comparison_type": data.get("kpi_comparison_type", "none"),
            "kpi_enable_target": data.get("kpi_enable_target", False),
            "kpi_target_value": data.get("kpi_target_value", 0),
            "kpi_view_type": data.get("kpi_view_type", "standard"),
            "kpi_same_period_previous_years": data.get(
                "kpi_same_period_previous_years", 0
            ),
            "previous_period_comparision": data.get(
                "previous_period_comparision", False
            ),
            "previous_period_duration": data.get("previous_period_duration", 0),
            "previous_period_type": data.get("previous_period_type", "percentage"),
        }
        for key, value in update_conf_dict.items():
            setattr(conf, key, value)

    def _process_domain(self, domain, extra_action, group_by_id):
        """
        Prepare domain
        """
        if extra_action and extra_action.get("domain"):
            domain = extra_action.get("prev_domains", domain)
            if extra_action.get("current_group_by"):
                group_by_id = group_by_id.browse(extra_action["current_group_by"])
            if group_by_id and group_by_id.ttype == "selection":
                value_name = False
                if isinstance(group_by_id.selection, str):
                    selections = safe_eval(group_by_id.selection)
                    for selection in selections:
                        if selection[1] == extra_action["domain"].get("record_id"):
                            value_name = selection[0]
                            break
                domain.append((group_by_id.name, "=", value_name))
            else:
                domain.append(
                    (group_by_id.name, "=", extra_action["domain"].get("record_id"))
                )
        return domain

    def get_tile_data(self, conf_obj, previous=0):
        """
        Calculate and get data for the Tile view
        """
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select model!"}
        if not conf_obj.measurement_field_id and conf_obj.data_type in [
            "sum",
            "average",
        ]:
            return {"type": "error", "message": "Please Select measurement!"}
        record_obj = self.env[conf_obj.model]
        message = ""
        today_date = False
        domain = conf_obj.domain.copy()
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))

        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_filter_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
                previous,
            )
            if date_filter_domain.get("domain"):
                start_date = date_filter_domain.get("start_date")
                end_date = date_filter_domain.get("end_date")
                message = "%s to %s" % (
                    start_date.strftime("%d %b, %y"),
                    end_date.strftime("%d %b, %y"),
                )
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_filter_domain["domain"])
                else:
                    today_date = start_date.date()

        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]

        count = 0
        if conf_obj.data_type == "count":
            count = len(all_records)
        elif conf_obj.data_type in ["sum", "average"]:
            count_list = [
                getattr(record, conf_obj.measurement_field_id.name)
                for record in all_records
            ]
            count = sum(count_list)
            if conf_obj.data_type == "average" and count != 0:
                count /= len(count_list)
        if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
            if conf_obj.data_type in ["count", "sum", "average"]:
                count *= conf_obj.chart_multiplier_ids[0].get("multiplier")
        count_with_symbol = round(count, 2)
        if conf_obj.show_unit:
            if conf_obj.unit_type == "monetary":
                company = self.env["res.company"].browse(conf_obj.company)
                count_with_symbol = format_amount(
                    record_obj.env, count_with_symbol, company.currency_id
                )
            else:
                count_with_symbol = "%s %s" % (
                    conf_obj.custom_unit or "",
                    count_with_symbol,
                )
        return {
            "name": conf_obj.name,
            "background_color": conf_obj.background_color,
            "is_kpi_border": conf_obj.is_kpi_border,
            "kpi_border_type": conf_obj.kpi_border_type,
            "kpi_border_color": conf_obj.kpi_border_color,
            "kpi_border_width": conf_obj.kpi_border_width,
            "font_color": conf_obj.font_color,
            "font_size": str(conf_obj.font_size),
            "font_weight": conf_obj.font_weight,
            "text_align": conf_obj.text_align,
            "count": count_with_symbol,
            "calculated_count": round(count, 2),
            "layout_type": conf_obj.layout_type,
            "tile_layout_type": conf_obj.tile_layout_type,
            "icon_option": conf_obj.icon_option,
            "default_icon": conf_obj.default_icon,
            "icon": conf_obj.icon,
            "message": message,
        }

    def get_kpi_data(self, conf_obj):
        """
        Calculate and get data for KPI view
        """

        def calc_ratio(tile_count, kpi_count2):
            """
            Calculation to calculate Ratio
            """
            n = gcd(int(tile_count), int(kpi_count2))
            return int(tile_count // n), int(kpi_count2 // n)

        def get_count2(records, conf):
            """
            Calculate second KPI data
            """
            if conf.kpi_data_type == "count":
                return len(records)
            elif conf.kpi_data_type in ("sum", "average"):
                values = [
                    getattr(rec, conf.kpi_measurement_field_id.name) for rec in records
                ]
                total = sum(values)
                return (
                    total / len(values)
                    if conf.kpi_data_type == "average" and values
                    else total
                )
            return 0

        prepared_data = self.get_tile_data(conf_obj)
        if prepared_data and prepared_data.get("type") == "error":
            return prepared_data

        if conf_obj.previous_period_comparision:
            updated_data = self.get_tile_data(
                conf_obj, conf_obj.previous_period_duration
            )
            if isinstance(updated_data, dict) and "type" in updated_data:
                updated_data.update(
                    {"calculated_count": 0, "message": updated_data["date_message"]}
                )
            if isinstance(updated_data, dict):
                standard = round(updated_data.get("calculated_count"), 2)
                if conf_obj.previous_period_type == "percentage":
                    standard = (
                        str(
                            round(
                                (updated_data.get("calculated_count") * 100)
                                / prepared_data.get("calculated_count"),
                                2,
                            )
                        )
                        + "%"
                        if prepared_data.get("calculated_count")
                        else "0 %"
                    )
                elif conf_obj.show_unit:
                    if conf_obj.unit_type == "monetary":
                        record_obj = self.env[conf_obj.model]
                        company = self.env["res.company"].browse(conf_obj.company)
                        standard = format_amount(
                            record_obj.env, standard, company.currency_id
                        )
                    else:
                        standard = "%s %s" % (
                            conf_obj.custom_unit or "",
                            standard,
                        )
                arrow = (
                    "up"
                    if prepared_data.get("calculated_count")
                    > updated_data.get("calculated_count")
                    else "down"
                )
                previous_data = {
                    "arrow": arrow,
                    "standard": standard,
                }
                if "message" in updated_data and updated_data.get("message"):
                    previous_data["message"] = updated_data["message"]
                prepared_data.update({"previous_data": previous_data})

        if not conf_obj.kpi_model:
            if conf_obj.kpi_enable_target:
                if conf_obj.kpi_view_type == "progress":
                    compute_count = prepared_data["calculated_count"]
                    target_value = conf_obj.kpi_target_value
                    progress = (
                        int(round((compute_count / target_value) * 100))
                        if target_value != 0
                        else 0
                    )
                    # if kcmp_type != "sum":
                    #     progress = int(compute_count) if compute_count else 0
                    prepared_data.update(
                        {
                            "kpi_view_type": "progress",
                            "progress": progress,
                            "kpi_enable_target": False,
                        }
                    )
                    # prepared_data.pop('previous_data')
                else:
                    compute_count = prepared_data["calculated_count"]
                    target_value = conf_obj.kpi_target_value
                    color, arrow = (
                        ("red", "down")
                        if (target_value - compute_count) > 0
                        else ("green", "up")
                    )
                    standard = (
                        str(
                            round(
                                (compute_count * 100) / target_value
                                if target_value != 0
                                else 1,
                                2,
                            )
                        )
                        + "%"
                    )
                    prepared_data.update(
                        {
                            "kpi_view_type": "standard",
                            "standard": standard,
                            "kpi_enable_target": False,
                            "color": color,
                            "arrow": arrow,
                        }
                    )
            return prepared_data

        if not conf_obj.kpi_measurement_field_id and conf_obj.kpi_data_type in (
            "sum",
            "average",
        ):
            return {"type": "error", "message": "Please Select measurement!"}

        record_obj = self.env[conf_obj.kpi_model]
        domain = conf_obj.kpi_domain[:]
        kpi_today_date = False
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.kpi_date_filter_field_id
            and conf_obj.kpi_date_filter_option
            and conf_obj.kpi_date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.kpi_date_filter_field_id,
                conf_obj.kpi_date_filter_option,
                conf_obj.kpi_include_periods,
                conf_obj.kpi_same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain += date_domain["domain"]
                else:
                    kpi_today_date = start_date.date()

        all_records = record_obj.search(domain)
        if kpi_today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.kpi_date_filter_field_id)
                and (
                    getattr(record, conf_obj.kpi_date_filter_field_id).date()
                    if isinstance(
                        getattr(record, conf_obj.kpi_date_filter_field_id), datetime
                    )
                    else getattr(record, conf_obj.kpi_date_filter_field_id)
                )
                == kpi_today_date
            )

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=conf_obj.sort_order == "desc",
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.kpi_limit_record > 0:
            all_records = all_records[: conf_obj.kpi_limit_record]

        count = prepared_data.get("calculated_count", 0)
        count2 = get_count2(all_records, conf_obj)
        compute_count = 0
        symbol = ""
        if conf_obj.show_unit:
            if conf_obj.unit_type == "monetary":
                company = self.env["res.company"].browse(conf_obj.company)
                symbol = "%s" % company.currency_id.symbol
            else:
                symbol = "%s" % (conf_obj.custom_unit or "")
        kcmp_type = conf_obj.kpi_comparison_type
        if kcmp_type == "sum":
            compute_count = count + count2
            prepared_data["count"] = "%s %s" % (symbol, round(compute_count, 2))
        elif kcmp_type == "percentage" and count2:
            compute_count = int((count / count2) * 100) if count2 else 0
            prepared_data["count"] = round(compute_count, 2)
        elif kcmp_type == "ratio" and count:
            compute_count, count2 = calc_ratio(count, count2)
            prepared_data.update(
                {
                    "count": "%s %s" % (symbol, round(compute_count, 2)),
                    "count2": "%s %s" % (symbol, count2),
                }
            )
        else:
            prepared_data["count2"] = round(count2, 2)

        if conf_obj.kpi_enable_target and kcmp_type in ("sum", "percentage"):
            target_value = conf_obj.kpi_target_value
            if conf_obj.kpi_enable_target == "percentage" and target_value > 100:
                target_value = 100

            color, arrow = (
                ("red", "down")
                if (target_value - compute_count) > 0
                else ("green", "up")
            )
            prepared_data.update(
                {"color": color, "arrow": arrow, "message": "vs Target"}
            )
            if conf_obj.kpi_view_type == "standard":
                diff = target_value - compute_count
                if diff <= 0:
                    diff = abs(diff)
                percent = round((diff / (target_value or 1)) * 100, 2)
                prepared_data["standard"] = f"{percent}%"
                if kcmp_type != "sum":
                    prepared_data["standard"] = min(target_value, 100)
            else:
                progress = (
                    int(round((compute_count / target_value) * 100))
                    if target_value != 0
                    else 0
                )
                if kcmp_type != "sum":
                    progress = int(compute_count) if compute_count else 0
                prepared_data.update({"progress": progress, "target": target_value})

        if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
            if conf_obj.data_type in ["count", "sum", "average"]:
                # prepared_data["count"] = float(prepared_data.get("count", 0)) * conf_obj.chart_multiplier_ids[0].get(
                #     "multiplier"
                # )
                count_multiply = (
                    round(compute_count, 2)
                    if compute_count
                    else float(prepared_data.get("calculated_count", 0))
                )
                prepared_data["count"] = count_multiply * conf_obj.chart_multiplier_ids[
                    0
                ].get("multiplier")

        prepared_data.update(
            {
                "comparison": kcmp_type,
                "kpi_view_type": conf_obj.kpi_view_type,
                "kpi_enable_target": conf_obj.kpi_enable_target,
            }
        )
        return prepared_data

    def get_todo_data(self, conf_obj):
        """
        Calculate and get TODO data
        """
        if conf_obj.todo_layout == "default" and not conf_obj.todo_action_ids:
            return {"type": "error", "message": "No Data found!"}
        if conf_obj.todo_layout == "activity" and not conf_obj.model:
            return {"type": "error", "message": "Please select Model!"}

        if conf_obj.todo_layout == "default":
            return {
                "layout_type": conf_obj.todo_layout,
                "name": conf_obj.name,
                "records": conf_obj.todo_action_ids,
            }

        today_date = False
        domain = conf_obj.domain
        record_obj = self.env[conf_obj.model]
        activities_domain = [("res_model", "=", conf_obj.model)]
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            # domain.extend(date_domain["domain"])
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    activities_domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(
            domain,
        )
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        activities_domain.extend([("res_id", "in", records.ids)])
        if conf_obj.limit_record == 0:
            activities = self.env["mail.activity"].search(
                activities_domain,
                order="create_date %s" % (conf_obj.sort_order or ""),
            )
        else:
            activities = self.env["mail.activity"].search(
                activities_domain,
                limit=conf_obj.limit_record or 100,
                order="create_date %s" % (conf_obj.sort_order or ""),
            )
        activities_data = [
            {
                "date": record.date_deadline,
                "summary": record.summary or "",
                "name": record.res_name,
                "username": record.user_id.name,
                "activity_type": record.activity_type_id.name,
            }
            for record in activities
        ]
        if not activities_data:
            return {"type": "error", "message": "No Data to display!"}
        return {
            "layout_type": conf_obj.todo_layout,
            "name": conf_obj.name,
            "records": activities_data,
        }

    def _get_view_item(self, extra_action):
        """
        To get chart views
        """
        if extra_action and self.item_view_action_ids:
            view_index = len(extra_action.get("breadcrump_ids", []))
            return (
                self.item_view_action_ids[view_index]
                if view_index < len(self.item_view_action_ids)
                else None
            )
        return None

    def _build_final_response(
        self, prepared_data, domain, chart_type, view_item, extra_action
    ):
        """
        Calculate final response for charts data
        """
        if not extra_action:
            return prepared_data
        if view_item:
            return {
                "prepared_data": prepared_data,
                "current_domain": domain,
                "current_group_by": view_item.group_by_id.id,
                "chart_type": view_item.chart_type,
                "breadcrump_ids": view_item.id,
            }
        if self.item_action_id:
            action = self.item_action_id.read()[0]
            action["domain"] = (
                self.evaluate_odoo_domain(action["domain"] or "[]")
            ) + domain
            return {"type": "action", "action": action}
        return prepared_data

    def get_measurement_fields(
        self,
        conf_obj,
        record,
        grouped_data,
        record_group_by,
        sub_groupby,
        measurement_multiplier_value,
    ):
        """
        Calculate Measurement fields
        """
        for measurement in conf_obj.measurement_field_ids:
            field_desc = measurement.field_description
            measure_value = getattr(record, measurement.name)
            multiplier = 1
            if conf_obj.is_apply_multiplier:
                matched = next(
                    (
                        m
                        for m in conf_obj.chart_multiplier_ids
                        if m.get("field_id") == measurement.id
                    ),
                    None,
                )
                if matched:
                    multiplier = matched.get("multiplier", 1)
                    if conf_obj.data_type == "sum":
                        measure_value *= multiplier
                    elif conf_obj.data_type == "average":
                        measurement_multiplier_value[field_desc] = multiplier
            key = (
                f"{sub_groupby} - {field_desc}"
                if conf_obj.sub_group_by
                else f" - {field_desc}"
            )
            if conf_obj.data_type == "sum":
                grouped_data[record_group_by][key] += measure_value
            elif conf_obj.data_type == "average":
                grouped_data[record_group_by].setdefault(key, []).append(measure_value)
        return grouped_data, measurement_multiplier_value

    def check_conf_obj(self, conf_obj, check_measure=False):
        """
        Check conf object data
        """
        check_constraint = False
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select Model!"}
        if (
            (not conf_obj.measurement_field_ids and not check_measure)
            or (not conf_obj.measurement_field_id and check_measure)
        ) and conf_obj.data_type != "count":
            check_constraint = {
                "type": "error",
                "message": "Please Select Measurements!",
            }
        if (
            not conf_obj.group_by
            and conf_obj.chart_type not in ["map_chart", "meter_chart"]
        ) or (conf_obj.chart_type == "map_chart" and not conf_obj.map_group_by):
            check_constraint = {"type": "error", "message": "Please Select Group by!"}
        return check_constraint

    def get_list_view_data(self, conf_obj):
        """
        This function is used in preparing data for List view
        """
        if not conf_obj.model:
            return {"type": "error", "message": "Please Select Model!"}
        if (conf_obj.list_type == "standard" and not conf_obj.list_field_ids) or (
            conf_obj.list_type == "grouped" and not conf_obj.list_measure_ids
        ):
            return {"type": "error", "message": "Please configure fields to display!"}
        if conf_obj.list_type == "grouped" and not conf_obj.group_by:
            return {"type": "error", "message": "Please Select Group by!"}
        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")
                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(domain)
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not records:
            return {"type": "error", "message": "No Data to display!"}

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = records.filtered(
                lambda rft: getattr(rft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= records.filtered(
                lambda rft: not getattr(rft, conf_obj.sort_field)
            )
            records = sorted_record
        if conf_obj.limit_record > 0:
            records = records[: conf_obj.limit_record]
        columns = []
        # column_names = []
        record_list = []
        ir_model_fields_obj = self.env["ir.model.fields"].sudo()
        if conf_obj.list_type == "standard":
            list_field_ids = sorted(
                conf_obj.list_field_ids, key=lambda x: x.get("sequence")
            )
            column_ids = [column.get("list_field_id") for column in list_field_ids]
            for column in column_ids:
                column_rec = ir_model_fields_obj.browse(column)
                columns.append(
                    {
                        "id": column_rec.id,
                        "column_name": column_rec.name,
                        "name": column_rec.field_description,
                    }
                )
            for record in records:
                record_set = {"id": record.id}
                for column in columns:
                    record_column_value = getattr(record, column.get("column_name"))
                    if isinstance(record_column_value, models.Model):
                        record_column_value = record_column_value.display_name
                    record_set.update(
                        {column.get("column_name"): record_column_value or ""}
                    )
                record_set["currentIds"] = [record.id]
                record_list.append(record_set)
        else:
            group_by_field = ir_model_fields_obj.search(
                [("name", "=", conf_obj.group_by), ("model", "=", conf_obj.model)],
                limit=1,
            )
            if group_by_field:
                columns.append(
                    {
                        "id": group_by_field.id,
                        "column_name": group_by_field.name,
                        "name": group_by_field.field_description,
                    }
                )
            for column in conf_obj.list_measure_ids:
                column_rec = ir_model_fields_obj.browse(column.get("list_measure_id"))
                columns.append(
                    {
                        "id": column_rec.id,
                        "column_name": column_rec.name,
                        "name": column_rec.field_description,
                        "value_type": column.get("value_type"),
                    }
                )
            grouped_by_records = groupby(
                records,
                key=lambda record: format_date_by_range(
                    getattr(record, conf_obj.group_by), conf_obj.time_range
                )
                if (
                    isinstance(getattr(record, conf_obj.group_by), (date, datetime))
                    and conf_obj.time_range
                )
                else getattr(record, conf_obj.group_by),
            )
            for group, grouped_records in grouped_by_records:
                record_set = {"id": group}
                for column in columns:
                    if column.get("column_name") == conf_obj.group_by:
                        record_value = group
                        if isinstance(record_value, models.Model):
                            record_value = group.display_name
                        record_set.update({column.get("column_name"): record_value})
                        continue
                    final_value = 0
                    for grouped_record in grouped_records:
                        final_value += getattr(
                            grouped_record, column.get("column_name")
                        )
                    if column.get("value_type") == "average" and final_value != 0:
                        final_value = final_value / len(grouped_records)
                    record_set.update(
                        {column.get("column_name"): round(final_value, 2)}
                    )
                currentIds = []
                for grouped_id in grouped_records:
                    currentIds.append(grouped_id.id)
                record_set["currentIds"] = currentIds
                record_list.append(record_set)
        return {
            "columns": columns,
            "records": record_list,
            "name": conf_obj.name,
            "model": conf_obj.model,
        }

    def get_measurement_group_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Area Chart
        Bar Chart
        Column Chart
        Doughnut Chart
        Line Chart
        StackedColumn Chart
        Radial Chart
        Scatter Chart
        """
        check_constraint = self.check_conf_obj(conf_obj)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        records = record_obj.search(domain)
        if today_date:
            records = records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not records:
            return {"type": "error", "message": "No Data to display!"}

        measurement_multiplier_value = {}

        grouped_data = defaultdict(lambda: defaultdict(float))

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = records.filtered(
                lambda rft: getattr(rft, conf_obj.sort_field)
            ).sorted(
                key=lambda sr: getattr(sr, conf_obj.sort_field).name
                if isinstance(getattr(sr, conf_obj.sort_field), models.Model)
                else getattr(sr, conf_obj.sort_field),
                reverse=conf_obj.sort_order == "desc",
            )
            sorted_record |= records.filtered(
                lambda rft: not getattr(rft, conf_obj.sort_field)
            )
            records = sorted_record
        if conf_obj.hide_false_value:
            records = records.filtered(lambda nonz: getattr(nonz, conf_obj.group_by))
            if conf_obj.sub_group_by:
                records = records.filtered(
                    lambda nonz: getattr(nonz, conf_obj.sub_group_by)
                )
        if conf_obj.limit_record > 0:
            records = records[: conf_obj.limit_record]

        for record in records:
            record_group_by = getattr(record, conf_obj.group_by)
            record_group_id = getattr(record, conf_obj.group_by)
            if hasattr(record._fields[conf_obj.group_by], "selection"):
                record_selections = record._fields[conf_obj.group_by].selection
                if isinstance(record_selections, str):
                    record_selections = dict(getattr(record, record_selections)())
                else:
                    record_selections = dict(record_selections)
                record_group_by = record_selections.get(
                    getattr(record, conf_obj.group_by)
                )
                record_group_id = record_selections.get(
                    getattr(record, conf_obj.group_by)
                )
            elif isinstance(record_group_by, models.Model):
                record_group_by = record_group_by.display_name
                record_group_id = record_group_id.id
            elif isinstance(record_group_by, (date, datetime)) and conf_obj.time_range:
                record_group_by = format_date_by_range(
                    record_group_by, conf_obj.time_range
                )
                record_group_id = format_date_by_range(
                    record_group_by, conf_obj.time_range
                )

            if conf_obj.sub_group_by:
                sub_groupby = getattr(record, conf_obj.sub_group_by)
                if hasattr(record._fields[conf_obj.sub_group_by], "selection"):
                    record_selections = record._fields[conf_obj.sub_group_by].selection
                    if isinstance(record_selections, str):
                        record_selections = dict(getattr(record, record_selections)())
                    else:
                        record_selections = dict(record_selections)
                    sub_groupby = record_selections.get(
                        getattr(record, conf_obj.sub_group_by)
                    )
                elif isinstance(sub_groupby, models.Model):
                    sub_groupby = sub_groupby.display_name
                elif (
                    isinstance(sub_groupby, (date, datetime))
                    and conf_obj.sub_time_range
                ):
                    sub_groupby = format_date_by_range(
                        sub_groupby, conf_obj.sub_time_range
                    )

                if conf_obj.data_type == "count":
                    grouped_data[(record_group_by, record_group_id)][
                        f"{sub_groupby} - count"
                    ] += 1
                if conf_obj.data_type in ["sum", "average"]:
                    grouped_data, measurement_multiplier_value = (
                        self.get_measurement_fields(
                            conf_obj,
                            record,
                            grouped_data,
                            (record_group_by, record_group_id),
                            sub_groupby,
                            measurement_multiplier_value,
                        )
                    )
            else:
                if conf_obj.data_type == "count":
                    grouped_data[(record_group_by, record_group_id)][" - count"] += 1
                if conf_obj.data_type in ["sum", "average"]:
                    grouped_data, measurement_multiplier_value = (
                        self.get_measurement_fields(
                            conf_obj,
                            record,
                            grouped_data,
                            (record_group_by, record_group_id),
                            False,
                            measurement_multiplier_value,
                        )
                    )

        result = []
        for customer, metrics in grouped_data.items():
            row = {
                "category": customer[0],
                "isSubGroupBy": conf_obj.sub_group_by,
                "record_id": customer[1],
            }
            row.update(metrics)
            if conf_obj.data_type == "average":
                for key, value in row.items():
                    if isinstance(value, list):
                        if len(value) != 0:
                            calc = sum(value) / len(value)
                            if (
                                conf_obj.is_apply_multiplier
                                and measurement_multiplier_value.get(key)
                            ):
                                calc = calc * measurement_multiplier_value.get(key)
                            row.update({key: calc})
                        else:
                            row.update({key: 0})
            result.append(row)

        if not result:
            return {"type": "error", "message": "No Data to display!"}

        value_keys = set()
        for row in result:
            value_keys.update(k for k in row if k not in ("category", "record_id"))
        if conf_obj.chart_type != "bar_chart":
            for row in result:
                for key in value_keys:
                    if key not in row:
                        row[key] = 0.0
        return result

    def check_category_config_type(self, conf_obj, records):
        """
        Check datatype of the conf object
        """
        total = sum(getattr(r, conf_obj.measurement_field_id.name) for r in records)
        category_value = (
            total / len(records) if conf_obj.data_type == "average" and total else total
        )
        if conf_obj.is_apply_multiplier:
            if multiplier := next(
                (
                    m["multiplier"]
                    for m in conf_obj.chart_multiplier_ids
                    if m["field_id"] == conf_obj.measurement_field_id.id
                ),
                None,
            ):
                category_value *= multiplier
        return category_value

    def get_category_value_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Funnel Chart
        Pie Chart
        Radar Chart
        """
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

        all_records = record_obj.search(domain)

        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        data_list = []
        if conf_obj.sort_order and conf_obj.sort_field:
            sort_records = self.env[conf_obj.model]
            sort_records |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field)
                if not isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field).display_name,
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sort_records |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sort_records

        if conf_obj.hide_false_value:
            all_records = all_records.filtered(
                lambda nonz: getattr(nonz, conf_obj.group_by)
            )
            if conf_obj.sub_group_by:
                all_records = all_records.filtered(
                    lambda nonz: getattr(nonz, conf_obj.sub_group_by)
                )
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]

        def group_by_func(rec):
            if not hasattr(rec._fields[conf_obj.group_by], "selection"):
                return getattr(rec, conf_obj.group_by)
            else:
                record_selections = rec._fields[conf_obj.group_by].selection
                if isinstance(record_selections, str):
                    record_selections = dict(getattr(rec, record_selections)())
                else:
                    record_selections = dict(record_selections)
                return record_selections.get(getattr(rec, conf_obj.group_by))

        for group_by, records in groupby(all_records, key=group_by_func):
            category_value = 0
            if conf_obj.data_type == "count":
                category_value = len(records)

            if conf_obj.data_type in ["sum", "average"]:
                category_value = self.check_category_config_type(conf_obj, records)
            if conf_obj.is_apply_multiplier and conf_obj.chart_multiplier_ids:
                if conf_obj.data_type in ["sum", "average", "count"]:
                    category_value *= conf_obj.chart_multiplier_ids[0].get("multiplier")
            category_instance = group_by
            record_id = group_by
            if isinstance(category_instance, models.Model):
                record_id = record_id.id
                category_instance = category_instance.display_name
            if conf_obj.hide_false_value and not category_instance:
                continue
            data_list.append(
                {
                    "category": category_instance,
                    "record_id": record_id,
                    "value": category_value,
                }
            )
        if not data_list:
            return {"type": "error", "message": "No Data to display!"}
        return sorted(
            data_list,
            key=lambda data: data.get("value"),
            reverse=conf_obj.sort_order == "desc",
        )

    def get_map_chart_data(self, conf_obj):
        """
        This function is used in preparing data for following charts
        Map Chart
        """
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

            if (
                start_date
                and end_date
                and start_date.date()
                and end_date.date()
                and start_date.date() != end_date.date()
            ):
                domain.extend(date_domain["domain"])
            else:
                today_date = start_date.date()

        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        data_list = []
        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = self.env[conf_obj.model]
            sorted_record |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field).name
                if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]
        if conf_obj.measurement_field_id:
            all_records = sorted(
                all_records,
                key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
            )

        for country_id, records in groupby(
            all_records,
            key=lambda rec: getattr(rec, conf_obj.map_group_by).country_id,
        ):
            category_value = 0
            if conf_obj.data_type == "sum":
                total_vals = []
                for record in records:
                    total_vals.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                category_value = sum(total_vals)
                if conf_obj.is_apply_multiplier:
                    filter_measure = list(
                        filter(
                            lambda measure: measure.get("field_id")
                            == conf_obj.measurement_field_id.id,
                            conf_obj.chart_multiplier_ids,
                        )
                    )
                    if filter_measure:
                        category_value = category_value * filter_measure[0].get(
                            "multiplier"
                        )
            elif conf_obj.data_type == "count":
                category_value = len(records)
            elif conf_obj.data_type == "average":
                total_vals = []
                for record in records:
                    total_vals.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                if sum(total_vals) != 0:
                    category_value = sum(total_vals) / len(records)
                if conf_obj.is_apply_multiplier:
                    filter_measure = list(
                        filter(
                            lambda measure: measure.get("field_id")
                            == conf_obj.measurement_field_id.id,
                            conf_obj.chart_multiplier_ids,
                        )
                    )
                    if filter_measure:
                        category_value = category_value * filter_measure[0].get(
                            "multiplier"
                        )
            if conf_obj.hide_false_value and (category_value == 0 or not country_id):
                continue
            data_list.append(
                {
                    "id": country_id.code,
                    "name": country_id.name,
                    "value": category_value,
                    "record_id": country_id.id,
                }
            )
        if not data_list:
            return {"type": "error", "message": "No Data to display!"}
        return data_list

    def get_meter_chart_data(self, conf_obj):
        check_constraint = self.check_conf_obj(conf_obj, True)
        if check_constraint:
            return check_constraint

        record_obj = self.env[conf_obj.model]
        today_date = False
        domain = conf_obj.domain
        if conf_obj.company and "company_id" in record_obj._fields:
            domain.append(("company_id", "in", [conf_obj.company, False]))
        if (
            conf_obj.date_filter_field
            and conf_obj.date_filter_option
            and conf_obj.date_filter_option != "none"
        ):
            date_domain = self.get_date_filter_domain(
                record_obj,
                conf_obj.date_filter_field,
                conf_obj.date_filter_option,
                conf_obj.include_periods,
                conf_obj.same_period_previous_years,
            )
            if date_domain.get("domain"):
                start_date = date_domain.get("start_date")
                end_date = date_domain.get("end_date")

            if (
                start_date
                and end_date
                and start_date.date()
                and end_date.date()
                and start_date.date() != end_date.date()
            ):
                domain.extend(date_domain["domain"])
            else:
                today_date = start_date.date()

        all_records = record_obj.search(domain)
        if today_date:
            all_records = all_records.filtered(
                lambda record: getattr(record, conf_obj.date_filter_field)
                and (
                    getattr(record, conf_obj.date_filter_field).date()
                    if isinstance(getattr(record, conf_obj.date_filter_field), datetime)
                    else getattr(record, conf_obj.date_filter_field)
                )
                == today_date
            )

        if not all_records:
            return {"type": "error", "message": "No Data to display!"}

        if conf_obj.sort_order and conf_obj.sort_field:
            sorted_record = self.env[conf_obj.model]
            sorted_record |= all_records.filtered(
                lambda arft: getattr(arft, conf_obj.sort_field)
            ).sorted(
                key=lambda rc: getattr(rc, conf_obj.sort_field).name
                if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                else getattr(rc, conf_obj.sort_field),
                reverse=True if conf_obj.sort_order == "desc" else False,
            )
            sorted_record |= all_records.filtered(
                lambda arft: not getattr(arft, conf_obj.sort_field)
            )
            all_records = sorted_record
        if conf_obj.limit_record > 0:
            all_records = all_records[: conf_obj.limit_record]
        if conf_obj.measurement_field_id:
            all_records = sorted(
                all_records,
                key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
            )

        total_vals = 0
        if conf_obj.data_type == "sum":
            total_vals_list = []
            for record in all_records:
                total_vals_list.append(
                    getattr(record, conf_obj.measurement_field_id.name)
                )
            total_vals = sum(total_vals_list)
        elif conf_obj.data_type == "average":
            if all_records:
                total_vals_list = []
                for record in all_records:
                    total_vals_list.append(
                        getattr(record, conf_obj.measurement_field_id.name)
                    )
                total_vals = sum(total_vals_list) / len(all_records)
        else:
            total_vals = len(all_records)

        target = conf_obj.meter_target
        if (
            conf_obj.date_filter_option
            not in [
                "none",
                "past_till_now",
                "past_excluding_today",
                "future_starting_now",
                "future_starting_tomorrow",
            ]
            and conf_obj.previous_period_comparision
        ):
            today_date = False
            domain = conf_obj.domain
            if conf_obj.company and "company_id" in record_obj._fields:
                domain.append(("company_id", "in", [conf_obj.company, False]))
            if (
                conf_obj.date_filter_field
                and conf_obj.date_filter_option
                and conf_obj.date_filter_option != "none"
            ):
                date_domain = self.get_date_filter_domain(
                    record_obj,
                    conf_obj.date_filter_field,
                    conf_obj.date_filter_option,
                    conf_obj.include_periods,
                    conf_obj.same_period_previous_years,
                    conf_obj.previous_period_duration,
                )
                if date_domain.get("domain"):
                    start_date = date_domain.get("start_date")
                    end_date = date_domain.get("end_date")

                if (
                    start_date
                    and end_date
                    and start_date.date()
                    and end_date.date()
                    and start_date.date() != end_date.date()
                ):
                    domain.extend(date_domain["domain"])
                else:
                    today_date = start_date.date()

            all_records = record_obj.search(domain)
            if today_date:
                all_records = all_records.filtered(
                    lambda record: getattr(record, conf_obj.date_filter_field)
                    and (
                        getattr(record, conf_obj.date_filter_field).date()
                        if isinstance(
                            getattr(record, conf_obj.date_filter_field), datetime
                        )
                        else getattr(record, conf_obj.date_filter_field)
                    )
                    == today_date
                )

            if not all_records:
                return {"type": "error", "message": "Target is not valid!"}

            if conf_obj.sort_order and conf_obj.sort_field:
                sorted_record = self.env[conf_obj.model]
                sorted_record |= all_records.filtered(
                    lambda arft: getattr(arft, conf_obj.sort_field)
                ).sorted(
                    key=lambda rc: getattr(rc, conf_obj.sort_field).name
                    if isinstance(getattr(rc, conf_obj.sort_field), models.Model)
                    else getattr(rc, conf_obj.sort_field),
                    reverse=True if conf_obj.sort_order == "desc" else False,
                )
                sorted_record |= all_records.filtered(
                    lambda arft: not getattr(arft, conf_obj.sort_field)
                )
                all_records = sorted_record
            if conf_obj.limit_record > 0:
                all_records = all_records[: conf_obj.limit_record]
            if conf_obj.measurement_field_id:
                all_records = sorted(
                    all_records,
                    key=lambda ao: getattr(ao, conf_obj.measurement_field_id.name),
                )

            target = 0
            if conf_obj.data_type == "sum":
                target = sum(all_records.mapped(conf_obj.measurement_field_id.name))
            elif conf_obj.data_type == "average":
                if all_records:
                    target_vals_list = []
                    for record in all_records:
                        target_vals_list.append(
                            getattr(record, conf_obj.measurement_field_id.name)
                        )
                    target = sum(target_vals_list) / len(all_records)
            else:
                target = len(all_records)
        if target <= 0:
            return {"type": "error", "message": "Target is not valid!"}
        return {
            "type": "success",
            "current_value": round(total_vals, 2),
            "target": target,
        }

    def get_date_filter_domain(
        self,
        model_obj,
        date_filter_field,
        date_filter_option,
        include_periods=0,
        same_period_previous_years=0,
        previous=0,
    ):
        """
        Prepare date filters domain based on configuration
        """
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        now = datetime.now()

        def start_end(dt, period, delta=relativedelta()):
            if period == "week":
                return dt - timedelta(days=dt.weekday()), dt + timedelta(days=6)
            elif period == "quarter":
                q = (dt.month - 1) // 3
                start = datetime(dt.year, 3 * q + 1, 1)
                return start, start + relativedelta(months=3) - timedelta(days=1)
            return dt.replace(day=1), dt.replace(day=1) + relativedelta(
                months=1
            ) - timedelta(days=1)

        date_ranges = {
            "today": (
                today - timedelta(days=previous),
                today - timedelta(days=previous),
            ),
            "this_week": start_end(today - relativedelta(weeks=previous), "week"),
            "this_month": start_end(today - relativedelta(months=previous), "month"),
            "this_quarter": start_end(
                today - relativedelta(months=previous * 3), "quarter"
            ),
            "this_year": (
                datetime(today.year - previous, 1, 1),
                datetime(today.year - previous, 12, 31),
            ),
            "week_to_date": (
                start_end(today - relativedelta(weeks=previous), "week")[0],
                today - relativedelta(weeks=previous),
            ),
            "month_to_date": (
                today.replace(day=1) - relativedelta(months=previous),
                today - relativedelta(months=previous),
            ),
            "quarter_to_date": (
                start_end(today - relativedelta(months=previous * 3), "quarter")[0],
                today,
            ),
            "year_to_date": (
                datetime(today.year - previous, 1, 1),
                today - relativedelta(years=previous),
            ),
            "next_day": (
                today - relativedelta(days=previous) + timedelta(days=1),
                today - relativedelta(days=previous) + timedelta(days=1),
            ),  # * 2
            "next_week": (
                start_end(today - relativedelta(weeks=previous), "week")[0]
                + timedelta(weeks=1),
                start_end(today - relativedelta(weeks=previous), "week")[1]
                + timedelta(weeks=1),
            ),
            "next_month": (
                start_end(today - relativedelta(months=previous), "month")[0]
                + relativedelta(months=1),
                start_end(today - relativedelta(months=previous), "month")[1]
                + relativedelta(months=1),
            ),
            "next_quarter": (
                start_end(today, "quarter")[0] + relativedelta(months=3),
                start_end(today, "quarter")[1] + relativedelta(months=3),
            ),
            "next_year": (
                datetime(today.year - previous + 1, 1, 1),
                datetime(today.year - previous + 1, 12, 31),
            ),
            "last_day": (
                today - relativedelta(days=previous) - timedelta(days=1),
                today - relativedelta(days=previous) - timedelta(days=1),
            ),  # * 2
            "last_week": (
                start_end(today - relativedelta(weeks=previous), "week")[0]
                - timedelta(weeks=1),
                start_end(today - relativedelta(weeks=previous), "week")[1]
                - timedelta(weeks=1),
            ),
            "last_month": (
                start_end(
                    today - relativedelta(months=previous) - relativedelta(months=1),
                    "month",
                )[0],
                start_end(
                    today - relativedelta(months=previous) - relativedelta(months=1),
                    "month",
                )[1],
            ),
            "last_quarter": (
                start_end(
                    today
                    - relativedelta(months=previous * 3)
                    - relativedelta(months=3),
                    "quarter",
                )[0],
                start_end(
                    today
                    - relativedelta(months=previous * 3)
                    - relativedelta(months=3),
                    "quarter",
                )[1],
            ),
            "last_year": (
                datetime(today.year - previous - 1, 1, 1),
                datetime(today.year - previous - 1, 12, 31),
            ),
            "last_seven_days": (
                today - relativedelta(days=7 * previous) - timedelta(days=7),
                today - relativedelta(days=7 * previous) - timedelta(seconds=1),
            ),
            "last_thirty_days": (
                today - relativedelta(days=30 * previous) - timedelta(days=30),
                today - relativedelta(days=30 * previous) - timedelta(seconds=1),
            ),
            "last_ninety_days": (
                today - relativedelta(days=90 * previous) - timedelta(days=90),
                today - relativedelta(days=90 * previous) - timedelta(seconds=1),
            ),
            "last_year_days": (
                today - relativedelta(years=previous) - timedelta(days=365),
                today - relativedelta(years=previous) - timedelta(seconds=1),
            ),
            "past_till_now": (datetime.min, now),
            "past_excluding_today": (datetime.min, today - timedelta(seconds=1)),
            "future_starting_today": (today, datetime.max),
            "future_starting_now": (now, datetime.max),
            "future_starting_tomorrow": (today + timedelta(days=1), datetime.max),
        }

        if date_filter_option not in date_ranges:
            return {"domain": [], "start_date": False, "end_date": False}

        base_start, base_end = date_ranges[date_filter_option]
        if include_periods > 0:
            base_end += (base_end - base_start) * include_periods

        domain = [
            (date_filter_field, ">=", base_start),
            (date_filter_field, "<=", base_end),
        ]
        for i in range(1, same_period_previous_years + 1):
            domain += [
                "|",
                (date_filter_field, ">=", base_start.replace(year=base_start.year - i)),
                (date_filter_field, "<=", base_end.replace(year=base_end.year - i)),
            ]
        return {
            "domain": domain,
            "start_date": base_start,
            "end_date": base_end.replace(
                hour=23, minute=59, second=59, microsecond=999999
            ),
        }


class ItemViewAction(models.Model):
    _name = "item.view.action"
    _description = "Item View Action"

    chart_id = fields.Many2one("dashboard.chart", string="Chart", ondelete="cascade")
    model_id = fields.Many2one("ir.model", string="Model", related="chart_id.model_id")
    group_by_id = fields.Many2one(
        "ir.model.fields", string="Action Group By", required=True, ondelete="cascade"
    )
    sort_field_id = fields.Many2one("ir.model.fields", string="Sort With")
    sort_order = fields.Selection(
        [("asc", "Ascending"), ("desc", "Descending")], string="Sort Order"
    )
    limit_record = fields.Integer(string="Record Limit", default=0)
    chart_type = fields.Selection(
        [
            ("bar_chart", "Bar Chart"),
            ("column_chart", "Column Chart"),
            ("doughnut_chart", "Doughnut Chart"),
            ("area_chart", "Area Chart"),
            ("funnel_chart", "Funnel Chart"),
            ("pyramid_chart", "Pyramid Chart"),
            ("line_chart", "Line Chart"),
            ("pie_chart", "Pie Chart"),
            ("radar_chart", "Radar Chart"),
            ("stackedcolumn_chart", "StackedColumn Chart"),
            ("radial_chart", "Radial Chart"),
            ("scatter_chart", "Scatter Chart"),
        ],
        default="bar_chart",
        required=True,
        string="Type",
    )

    @api.constrains("limit_record")
    def _check_limit_record(self):
        for item in self:
            if item.limit_record and item.limit_record < 0:
                raise ValidationError(
                    _(
                        "Oops! The record limit can’t be less than zero. Please enter a value of zero or higher to continue."
                    )
                )


class ChartMultiplier(models.Model):
    _name = "chart.multiplier"
    _description = "Chart Multiplier"

    chart_id = fields.Many2one("dashboard.chart", string="Chart", ondelete="cascade")
    field_id = fields.Many2one("ir.model.fields", string="Multiplier field")
    multiplier = fields.Float(string="Multiplier", default=1.0)

    @api.constrains("multiplier")
    def _check_limit_multiplier(self):
        for rec in self:
            if rec.multiplier and rec.multiplier < 0:
                raise ValidationError(
                    _(
                        "The multiplier must be 1 or greater. Please enter a valid value to proceed."
                    )
                )

    @api.onchange("multiplier")
    def _onchange_multiplier(self):
        if self.multiplier and self.multiplier < 0:
            return {
                "warning": {
                    "title": _("Warning"),
                    "message": _(
                        "The multiplier must be 1 or greater. Please enter a valid value to proceed."
                    ),
                }
            }
