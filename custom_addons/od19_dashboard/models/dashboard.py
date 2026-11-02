import json
import logging
from datetime import date, datetime, timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import format_date, format_datetime
from odoo.tools.safe_eval import safe_eval

from . import dashboard_formula as formula_tools
from .dashboard_rule import COMPARE_TYPES, OPERATORS

_logger = logging.getLogger(__name__)

WIDGET_TYPES = [
    ("kpi", "KPI Value"),
    ("bar", "Bar Chart"),
    ("line", "Line Chart"),
    ("pie", "Pie Chart"),
    ("list", "List"),
]

VALUE_FORMATS = [
    ("number", "Number"),
    ("currency", "Currency"),
    ("percent", "Percent"),
    ("hours", "Hours"),
]

AUDIENCES = [
    ("owner", "Owner / Executive"),
    ("management", "Management"),
    ("operational", "Operational Lead"),
]

DATE_RANGES = [
    ("all_time", "All Time"),
    ("today", "Today"),
    ("yesterday", "Yesterday"),
    ("last_7_days", "Last 7 Days"),
    ("last_30_days", "Last 30 Days"),
    ("last_90_days", "Last 90 Days"),
    ("this_month", "This Month"),
    ("this_quarter", "This Quarter"),
    ("this_year", "This Year"),
    ("next_7_days", "Next 7 Days"),
    ("overdue", "Overdue"),
]

FORMULA_MODES = [
    ("measure", "Single measure"),
    ("preset", "Preset formula"),
    ("custom", "Custom expression"),
    ("library", "Library formula"),
]

#: Preset formulas whose slot list is filled by the designer (a, b, c, d, e).
VARIADIC_FORMULA_TYPES = ("sum", "average")

FORMULA_BASIS = [
    ("previous", "Previous period"),
    ("yty", "Same period last year"),
    ("mtm", "Previous month"),
    ("qtq", "Previous quarter"),
]

STATUS_SELECTION = [
    ("red", "Red"),
    ("yellow", "Yellow"),
    ("green", "Green"),
    ("grey", "Grey"),
]

#: Colours the client paints the chart buckets and the list rows with.
STATUS_COLORS = {
    "red": "#9E2424",
    "yellow": "#B7791F",
    "green": "#2E7D32",
    "grey": "#6B7280",
}

#: Severity of a bucket status; the widget keeps the most severe one.
STATUS_SEVERITY = {"grey": 0, "green": 1, "yellow": 2, "red": 3}

# Grid limits shared with the front-end builder.
MIN_GRID_W, MAX_GRID_W = 2, 12
MIN_GRID_H, MAX_GRID_H = 1, 6


class Od19Dashboard(models.Model):
    _name = "od19.dashboard"
    _description = "Dashboard"
    _order = "audience, sequence, name"

    name = fields.Char(required=True)
    audience = fields.Selection(
        selection=AUDIENCES,
        required=True,
        default="management",
        help="Role this dashboard is designed for, as defined in the dashboard blueprint.",
    )
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        help="User who designed the dashboard and can keep editing it.",
    )
    group_ids = fields.Many2many(
        "res.groups",
        "od19_dashboard_group_rel",
        "dashboard_id",
        "group_id",
        string="Visible to Groups",
        help="Leave empty to make the dashboard visible to every internal user.",
    )
    user_ids = fields.Many2many(
        "res.users",
        "od19_dashboard_user_rel",
        "dashboard_id",
        "user_id",
        string="Visible to Users",
    )

    is_default = fields.Boolean(
        help="Default dashboard offered to the audience when no dashboard is selected.",
    )
    shared = fields.Boolean(
        default=True,
        help="Uncheck to keep the dashboard private to its owner.",
    )
    default_date_range = fields.Selection(
        selection=DATE_RANGES,
        default="last_30_days",
        required=True,
    )
    color = fields.Char(
        default="#9E2424",
        help="Accent colour used by the dashboard header.",
    )

    widget_ids = fields.One2many(
        "od19.dashboard.widget",
        "dashboard_id",
        string="Widgets",
        copy=True,
    )
    widget_count = fields.Integer(compute="_compute_widget_count")

    _name_company_default = models.Constraint(
        "unique(name, company_id)",
        "A dashboard with this name already exists for this company.",
    )

    @api.depends("widget_ids")
    def _compute_widget_count(self):
        for dashboard in self:
            dashboard.widget_count = len(dashboard.widget_ids)

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------
    def _can_edit(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group("od19_dashboard.group_od19_dashboard_manager"):
            return True
        return self.owner_id == user and user.has_group(
            "od19_dashboard.group_od19_dashboard_user"
        )

    def _check_edit_access(self):
        self.ensure_one()
        if not self._can_edit():
            raise AccessError(_("You are not allowed to design this dashboard."))

    # ------------------------------------------------------------------
    # Front-end API
    # ------------------------------------------------------------------
    @api.model
    def get_user_dashboards(self):
        """Return dashboards readable by the current user for the selector."""
        dashboards = self.search([("active", "=", True)])
        audience_labels = dict(self._fields["audience"].selection)
        return [
            {
                "id": dashboard.id,
                "name": dashboard.name,
                "audience": dashboard.audience,
                "audience_label": audience_labels.get(dashboard.audience, dashboard.audience),
                "is_default": dashboard.is_default,
                "can_edit": dashboard._can_edit(),
                "shared": dashboard.shared,
            }
            for dashboard in dashboards
        ]

    @api.model
    def get_builder_meta(self):
        """Return everything the builder dialog needs to render its forms."""
        sources = self.env["od19.dashboard.source"].search([("active", "=", True)])
        formulas = self.env["od19.dashboard.formula"].search([("active", "=", True)])
        company = self.env.company
        return {
            "sources": [source._to_meta() for source in sources],
            "formulas": [formula._to_meta() for formula in formulas],
            "widget_types": [{"key": key, "label": label} for key, label in WIDGET_TYPES],
            "value_formats": [{"key": key, "label": label} for key, label in VALUE_FORMATS],
            "formula_modes": [{"key": key, "label": label} for key, label in FORMULA_MODES],
            "formula_types": [
                {
                    "key": key,
                    "label": label,
                    "slots": list(formula_tools.PRESET_REQUIRED_SLOTS.get(key, ())),
                    "variadic": key in VARIADIC_FORMULA_TYPES,
                    "expression": formula_tools.PRESET_EXPRESSIONS.get(key, ""),
                }
                for key, label in formula_tools.FORMULA_TYPES
            ],
            "compare_types": [{"key": key, "label": label} for key, label in COMPARE_TYPES],
            "operators": [{"key": key, "label": label} for key, label in OPERATORS],
            "statuses": [{"key": key, "label": label} for key, label in STATUS_SELECTION],
            "status_colors": dict(STATUS_COLORS),
            "period_bases": [{"key": key, "label": label} for key, label in FORMULA_BASIS],
            "date_ranges": [{"key": key, "label": label} for key, label in DATE_RANGES],
            "audiences": [{"key": key, "label": label} for key, label in AUDIENCES],
            "currency": {
                "symbol": company.currency_id.symbol or "",
                "position": company.currency_id.position or "before",
                "decimal_places": company.currency_id.decimal_places or 2,
            },
            "grid": {"min_w": MIN_GRID_W, "max_w": MAX_GRID_W, "min_h": MIN_GRID_H, "max_h": MAX_GRID_H},
        }

    @api.model
    def get_dashboard_data(self, dashboard_id, date_range=None, date_from=None, date_to=None):
        """Return the dashboard definition and the computed value of every widget."""
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard.check_access("read")

        widgets = []
        widget_values = {}
        for widget in dashboard._compute_order():
            dashboard._resolve_dependency_values(widget, widget_values)
            data = widget._get_widget_data(
                date_range, date_from, date_to, widget_values=widget_values
            )
            widget_values[widget.id] = data.get("value")
            data["config"] = widget._to_config()
            widgets.append(data)

        return {
            "dashboard": {
                "id": dashboard.id,
                "name": dashboard.name,
                "audience": dashboard.audience,
                "description": dashboard.description or "",
                "color": dashboard.color or "#9E2424",
                "default_date_range": dashboard.default_date_range,
                "can_edit": dashboard._can_edit(),
                "owner_name": dashboard.owner_id.name,
            },
            "widgets": widgets,
            "meta": {
                "date_range": date_range or None,
                "date_from": date_from or None,
                "date_to": date_to or None,
                "default_date_range": dashboard.default_date_range,
                "generated_at": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    def _compute_order(self):
        """Return the active widgets of this dashboard in dependency order.

        A widget is emitted only once every widget it reads has been emitted,
        so a rule can compare with an already computed value. Sequence (then
        id) breaks ties, which keeps the visual order stable. A cycle cannot be
        solved: it is logged and the remaining widgets are emitted in sequence
        order, which keeps the dashboard usable (fail soft).
        """
        self.ensure_one()
        pending = {widget.id: widget for widget in self.widget_ids.filtered("active")}
        ordered = []
        while pending:
            ready = [
                widget
                for widget in pending.values()
                if all(dependency not in pending for dependency in widget._dependency_ids())
            ]
            if not ready:
                _logger.warning(
                    "Dashboard %s has a circular widget dependency, falling back to sequence order: %s",
                    self.id,
                    sorted(pending),
                )
                ready = list(pending.values())
            for widget in sorted(ready, key=lambda item: (item.sequence, item.id)):
                ordered.append(widget)
                pending.pop(widget.id)
        return ordered

    def _dependency_closure(self):
        """Return every active widget reachable from this dashboard.

        A status rule may compare with a widget of another dashboard (spec
        phase 2, section 6), so the graph is not limited to ``widget_ids``. The
        closure is what ``_check_no_cycle()`` sorts to spot a loop. An archived
        widget is left out: it is no longer part of the live graph, so the
        widgets reading it can settle again.
        """
        self.ensure_one()
        closure = {}
        pending = list(self.widget_ids.filtered("active"))
        while pending:
            widget = pending.pop()
            if widget.id in closure:
                continue
            closure[widget.id] = widget
            for dependency_id in widget._dependency_ids():
                if dependency_id in closure:
                    continue
                other = self.env["od19.dashboard.widget"].browse(dependency_id).exists()
                if other and other.active:
                    pending.append(other)
        return closure

    def _resolve_dependency_values(self, widget, widget_values, stack=None):
        """Fill ``widget_values`` with the value of every widget ``widget`` reads.

        A dependency of another dashboard cannot be reached by
        ``_compute_order()`` (it is not part of this dashboard), so it is
        computed here, lazily and recursively. ``stack`` guards a cross
        dashboard loop: a widget already being resolved falls back to ``None``
        (fail soft) instead of looping forever.
        """
        self.ensure_one()
        stack = set(stack or ())
        stack.add(widget.id)
        for dependency_id in widget._dependency_ids():
            if dependency_id in widget_values or dependency_id in stack:
                widget_values.setdefault(dependency_id, None)
                continue
            other = self.env["od19.dashboard.widget"].browse(dependency_id).exists()
            if not other:
                widget_values[dependency_id] = None
                continue
            self._resolve_dependency_values(other, widget_values, stack)
            data = other._get_widget_data(widget_values=widget_values)
            widget_values[dependency_id] = data.get("value")
        return widget_values

    def _check_no_cycle(self):
        """Refuse a widget graph that never settles (spec section 11).

        ``_compute_order()`` resolves the same edges but fails soft at render
        time; saving must fail hard so an unsolvable dashboard is never stored.
        The graph is walked across dashboards because a rule may compare with a
        widget of another dashboard.
        """
        self.ensure_one()
        pending = self._dependency_closure()
        try:
            while pending:
                ready = [
                    widget
                    for widget in pending.values()
                    if all(dependency not in pending for dependency in widget._dependency_ids())
                ]
                if not ready:
                    names = ", ".join(
                        sorted(widget.name or str(widget.id) for widget in pending.values())
                    )
                    raise ValidationError(
                        _(
                            "These widgets read each other in a loop: %s. "
                            "Remove one of the references so the values can be computed."
                        )
                        % names
                    )
                for widget in ready:
                    pending.pop(widget.id)
        finally:
            # Walking the graph reads ``rule_ids``, which caches the one2many.
            # Odoo appends a later rule to that cached list instead of reading
            # the table, so the cache has to be dropped to keep ``_order``.
            self.widget_ids.invalidate_recordset(["rule_ids"])

    def _preview_dependency_ids(self, draft):
        """Return the ids of the stored widgets ``draft`` reads, transitively.

        A draft is not part of the dashboard, so its own dependencies never
        appear in ``_compute_order()``. Walking them here keeps the preview
        cheap: only the widgets the formula actually reads are computed.
        """
        self.ensure_one()
        by_id = {widget.id: widget for widget in self.widget_ids.filtered("active")}
        needed = set()
        pending = list(draft._dependency_ids())
        while pending:
            widget_id = pending.pop()
            if widget_id in needed or widget_id not in by_id:
                continue
            needed.add(widget_id)
            pending.extend(by_id[widget_id]._dependency_ids())
        return needed

    @api.model
    def _normalise_preview_values(self, values):
        """Return builder values usable to build an in-memory widget record.

        ``id`` is dropped (it would bind the new record to a stored one) and
        ``rule_ids`` is rewritten as create commands so a draft always carries
        brand new rules, whether the builder sent an existing rule, a modified
        rule or a deleted one.
        """
        cleaned = dict(values or {})
        cleaned.pop("id", None)
        commands = []
        for rule in cleaned.get("rule_ids") or []:
            if isinstance(rule, (list, tuple)):
                code = rule[0] if rule else 0
                # Only a create (0) or an update (1) command carries the values
                # of a rule. A link (4), a clear (5) or a delete (2, 3, 6) is
                # dropped: the draft always carries brand new rules.
                if code not in (0, 1) or len(rule) < 3 or not isinstance(rule[2], dict):
                    continue
                data = dict(rule[2])
            else:
                data = dict(rule)
            data.pop("id", None)
            data.pop("widget_id", None)
            commands.append((0, 0, data))
        cleaned["rule_ids"] = commands
        return cleaned

    @api.model
    def preview_widget(self, values, date_range=None):
        """Evaluate a draft widget configuration without writing to the database.

        The builder calls this on every change so the designer immediately sees
        the value, the number of records the widget would collect, the status
        resulting from the rule list, and the operands actually used. The draft
        lives in a new (in-memory) record: nothing is stored.
        """
        cleaned = self._normalise_preview_values(values)
        draft = self.env["od19.dashboard.widget"].new(cleaned)
        draft._validate_formula_config()

        dashboard = draft.dashboard_id
        wanted = set()
        if dashboard:
            dashboard.check_access("read")
            wanted = dashboard._preview_dependency_ids(draft)

        effective_range = date_range or cleaned.get("date_range")
        widget_values = {}
        if dashboard:
            for widget in dashboard._compute_order():
                if widget.id not in wanted:
                    continue
                dashboard._resolve_dependency_values(widget, widget_values)
                other = widget._get_widget_data(
                    date_range=effective_range, widget_values=widget_values
                )
                widget_values[widget.id] = other.get("value")
            dashboard._resolve_dependency_values(draft, widget_values)

        data = draft._get_widget_data(date_range=effective_range, widget_values=widget_values)
        return {
            "value": data.get("value"),
            "value_text": data.get("value_text") or "",
            "record_count": data.get("record_count") or 0,
            "status": data.get("status"),
            "status_source": data.get("status_source") or "default",
            "status_message": data.get("status_message") or "",
            "visible": data.get("visible", True),
            "operands": data.get("operands") or [],
            "series_preview": (data.get("series") or [])[:5],
            "formula_expression": draft._effective_expression(),
            "message": data.get("message") or "",
        }

    @api.model
    def save_layout(self, dashboard_id, layout):
        """Persist the order / size of the widgets after a drag or resize."""
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard.check_access("write")
        dashboard._check_edit_access()

        for item in layout or []:
            widget = dashboard.widget_ids.filtered(lambda w: w.id == item.get("id"))
            if not widget:
                continue
            widget.write(
                {
                    "sequence": int(item.get("sequence", widget.sequence) or 0),
                    "grid_w": min(max(int(item.get("grid_w", widget.grid_w) or widget.grid_w), MIN_GRID_W), MAX_GRID_W),
                    "grid_h": min(max(int(item.get("grid_h", widget.grid_h) or widget.grid_h), MIN_GRID_H), MAX_GRID_H),
                }
            )
        return True

    @api.model
    def create_widget(self, dashboard_id, values):
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        dashboard._check_edit_access()
        dashboard.check_access("write")

        values = dict(values or {})
        values["dashboard_id"] = dashboard.id
        if not values.get("sequence"):
            last = dashboard.widget_ids.mapped("sequence")
            values["sequence"] = (max(last) + 10) if last else 10
        self._clamp_grid_values(values)
        widget = self.env["od19.dashboard.widget"].create(values)
        return {"id": widget.id, "config": widget._to_config()}

    @api.model
    def _clamp_grid_values(self, values, widget=None):
        """Keep the widget grid size inside the ranges the dashboard offers."""
        for key, low, high, default in (
            ("grid_w", MIN_GRID_W, MAX_GRID_W, 4),
            ("grid_h", MIN_GRID_H, MAX_GRID_H, 2),
        ):
            if key not in values:
                continue
            current = (widget[key] if widget is not None else 0) or default
            values[key] = min(max(int(values.get(key) or current), low), high)
        return values

    @api.model
    def update_widget(self, widget_id, values):
        widget = self.env["od19.dashboard.widget"].browse(widget_id).exists()
        if not widget:
            raise UserError(_("This widget does not exist or is no longer available."))
        widget.dashboard_id._check_edit_access()
        widget.check_access("write")
        widget.write(self._clamp_grid_values(dict(values or {}), widget))
        return {"id": widget.id, "config": widget._to_config()}

    @api.model
    def delete_widget(self, widget_id):
        widget = self.env["od19.dashboard.widget"].browse(widget_id).exists()
        if not widget:
            return True
        widget.dashboard_id._check_edit_access()
        widget.check_access("unlink")
        widget.unlink()
        return True

    @api.model
    def duplicate_dashboard(self, dashboard_id, new_name=None):
        """Copy a dashboard into a private one owned by the current user.

        A designer may copy any dashboard they can read, including the shared
        baseline dashboards, which is how the delivered roles are customised.
        """
        dashboard = self.browse(dashboard_id).exists()
        if not dashboard:
            raise UserError(_("This dashboard does not exist or is no longer available."))
        if not self.env.user.has_group("od19_dashboard.group_od19_dashboard_user"):
            raise AccessError(_("You need the Dashboard Designer role to copy a dashboard."))
        dashboard.check_access("read")
        new_dashboard = dashboard.copy(
            {
                "name": new_name or _("%s (copy)") % dashboard.name,
                "owner_id": self.env.user.id,
                "is_default": False,
            }
        )
        return new_dashboard.id


class Od19DashboardWidget(models.Model):
    _name = "od19.dashboard.widget"
    _description = "Dashboard Widget"
    _order = "dashboard_id, sequence, id"

    dashboard_id = fields.Many2one(
        "od19.dashboard",
        required=True,
        ondelete="cascade",
        index=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    name = fields.Char(required=True, default=lambda self: _("New Widget"))
    subtitle = fields.Char()
    widget_type = fields.Selection(
        selection=WIDGET_TYPES,
        required=True,
        default="kpi",
    )
    value_format = fields.Selection(
        selection=VALUE_FORMATS,
        required=True,
        default="number",
    )
    color = fields.Char(help="Optional accent colour for the widget header.")

    source_id = fields.Many2one(
        "od19.dashboard.source",
        required=True,
        ondelete="restrict",
        string="Data Source",
    )
    model_name = fields.Char(related="source_id.model_name", string="Model")
    measure_key = fields.Char(
        required=True,
        default="__count",
        help="Field of the data source used as measure, or '__count'.",
    )
    groupby_key = fields.Char(help="Field of the data source used to group the values.")
    date_key = fields.Char(help="Date field of the data source used for the period filter.")
    date_range = fields.Selection(selection=DATE_RANGES, default="last_30_days", required=True)
    domain = fields.Char(
        default="[]",
        help="Additional Odoo domain applied to the data source, as a Python list.",
    )
    limit = fields.Integer(default=10)

    goal_value = fields.Float()
    show_delta = fields.Boolean(default=True, string="Show Period Comparison")

    formula_mode = fields.Selection(
        selection=FORMULA_MODES,
        default="measure",
        required=True,
        help="Single measure keeps the historical behaviour; preset and custom "
        "let the user combine several measures.",
    )
    formula_type = fields.Selection(
        selection=formula_tools.FORMULA_TYPES,
        help="Used when the formula mode is 'Preset formula'.",
    )
    formula_slots = fields.Text(
        default="{}",
        help="JSON mapping of slot to measure, e.g. "
        '{"a": "amount_total", "b": "__count"}. Weight slots w1 / w2 hold numbers.',
    )
    formula_expression = fields.Char(
        help="Expression evaluated with safe_eval, used when the formula mode is 'Custom expression'.",
    )
    formula_id = fields.Many2one(
        "od19.dashboard.formula",
        ondelete="restrict",
        string="Library Formula",
        help="Named formula picked from the library, used when the formula mode is 'Library formula'.",
    )
    visible_expression = fields.Char(
        help="Condition hiding the widget when it evaluates to 0 / False. "
        "Empty means the widget is always shown.",
    )
    formula_basis = fields.Selection(
        selection=FORMULA_BASIS,
        default="previous",
        required=True,
        help="Reference period of the growth and cumulative change formulas.",
    )
    delta_basis = fields.Selection(
        selection=FORMULA_BASIS,
        default="previous",
        required=True,
        help="Reference period of the period comparison shown on a KPI. "
             "Previous month / quarter shift the whole period window back by one "
             "month or three months, keeping its length.",
    )
    default_status = fields.Selection(
        selection=STATUS_SELECTION,
        default="green",
        required=True,
        help="Status used when no status rule matches.",
    )
    rule_ids = fields.One2many(
        "od19.dashboard.widget.rule",
        "widget_id",
        string="Status Rules",
        copy=True,
    )

    grid_w = fields.Integer(default=4, string="Width (columns)")
    grid_h = fields.Integer(default=2, string="Height (rows)")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains("widget_type", "groupby_key")
    def _check_groupby_required(self):
        for widget in self:
            if widget.widget_type in ("bar", "line", "pie") and not widget.groupby_key:
                raise ValidationError(
                    _("Chart widgets require a group by field (widget: %s).") % widget.name
                )

    @api.constrains("measure_key", "groupby_key", "date_key", "source_id")
    def _check_source_fields(self):
        for widget in self:
            source = widget.source_id
            if not source:
                continue
            if widget.measure_key and widget.measure_key != "__count" and not source._measure_field(widget.measure_key):
                raise ValidationError(
                    _("Measure '%s' is not available on data source '%s'.")
                    % (widget.measure_key, source.name)
                )
            if widget.groupby_key and not source._groupby_field(widget.groupby_key):
                raise ValidationError(
                    _("Group by '%s' is not available on data source '%s'.")
                    % (widget.groupby_key, source.name)
                )
            if widget.date_key and not source._date_field(widget.date_key):
                raise ValidationError(
                    _("Date field '%s' is not available on data source '%s'.")
                    % (widget.date_key, source.name)
                )

    @api.constrains("domain")
    def _check_domain(self):
        for widget in self:
            if not (widget.domain or "").strip():
                continue
            try:
                parsed = safe_eval(widget.domain)
            except Exception as error:  # noqa: BLE001 - surface the parsing error to the user
                raise ValidationError(
                    _("The filter of widget '%s' is not a valid domain: %s") % (widget.name, error)
                ) from error
            if not isinstance(parsed, list):
                raise ValidationError(
                    _("The filter of widget '%s' must be a list (Odoo domain).") % widget.name
                )

    @api.constrains(
        "formula_mode",
        "formula_type",
        "formula_slots",
        "formula_expression",
        "formula_id",
        "visible_expression",
        "formula_basis",
        "delta_basis",
        "source_id",
        "measure_key",
        "rule_ids",
    )
    def _check_formula_config(self):
        self._validate_formula_config()

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def _to_config(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle or "",
            "widget_type": self.widget_type,
            "value_format": self.value_format,
            "color": self.color or "",
            "source_id": self.source_id.id,
            "measure_key": self.measure_key,
            "groupby_key": self.groupby_key or "",
            "date_key": self.date_key or "",
            "date_range": self.date_range,
            "domain": self.domain or "[]",
            "limit": self.limit,
            "goal_value": self.goal_value,
            "show_delta": self.show_delta,
            "formula_mode": self.formula_mode,
            "formula_type": self.formula_type or "",
            "formula_slots": self.formula_slots or "{}",
            "formula_expression": self._effective_expression(),
            "formula_id": self.formula_id.id,
            "visible_expression": self.visible_expression or "",
            "formula_basis": self.formula_basis,
            "delta_basis": self.delta_basis,
            "default_status": self.default_status,
            "rule_ids": [rule._to_values() for rule in self.rule_ids],
            "grid_w": self.grid_w,
            "grid_h": self.grid_h,
            "sequence": self.sequence,
        }

    # ------------------------------------------------------------------
    # Data computation
    # ------------------------------------------------------------------
    def _get_widget_data(self, date_range=None, date_from=None, date_to=None, widget_values=None):
        self.ensure_one()
        data = {
            "id": self.id,
            "name": self.name,
            "subtitle": self.subtitle or "",
            "widget_type": self.widget_type,
            "value_format": self.value_format,
            "color": self.color or "",
            "goal_value": self.goal_value,
            "delta_basis": self.delta_basis,
            "is_lower_better": self._is_lower_better(),
            "grid_w": self.grid_w,
            "grid_h": self.grid_h,
            "sequence": self.sequence,
            "status": "grey",
            "status_source": "default",
            "status_message": "",
            "visible": True,
            "value": None,
            "value_text": "",
            "record_count": 0,
            "delta": None,
            "series": [],
            "rows": [],
            "operands": [],
            "formula_expression": self._effective_expression(),
            "message": False,
        }

        source = self.source_id
        if not source or not source.model_name or source.model_name not in self.env:
            data["message"] = _("The data source of this widget is not installed in this database.")
            return data

        model = self.env[source.model_name]
        try:
            model.check_access("read")
        except AccessError:
            data["message"] = _("You do not have read access on %s.") % source.name
            return data

        requests = self._aggregate_requests()
        if not requests:
            data["message"] = _("The measure configured on this widget is not available any more.")
            return data

        try:
            domain = self._build_domain(date_range, date_from, date_to)
        except ValidationError as error:
            data["message"] = str(error)
            return data

        try:
            if self.widget_type == "kpi":
                self._fill_kpi_data(data, model, domain, requests, date_range, date_from, date_to, widget_values)
            elif self.widget_type in ("bar", "line", "pie"):
                self._fill_chart_data(data, model, domain, requests, date_range, date_from, date_to, widget_values)
            else:
                self._fill_list_data(data, model, domain)
        except (AccessError, UserError) as error:
            data["message"] = str(error)
            data["status"] = "grey"
            data["status_source"] = "default"
        except Exception as error:  # noqa: BLE001 - never break the whole dashboard
            _logger.exception("Dashboard widget %s could not be computed", self.id)
            data["message"] = _("This widget could not be computed: %s") % error
            data["status"] = "grey"
            data["status_source"] = "default"
        if (self.visible_expression or "").strip():
            data["visible"] = self._is_visible(
                self._visibility_context(data, widget_values)
            )
        return data

    def _fill_kpi_data(self, data, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        if self._needs_bounded_period() and not self._run_rate_days(date_range, date_from, date_to):
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [], aggregates, limit=1)
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        context = self._formula_context(rows[0] if rows else (), requests, extra)
        # The operands and the record count are published before the value is
        # evaluated: the builder must still list the operands it read when the
        # formula cannot be evaluated (a division by zero on an empty period,
        # for instance) and the value is reported as a message instead.
        data["record_count"] = self._record_count(model, domain)
        data["operands"] = self._operand_details(requests, context)
        value = self._evaluate_value(context)
        if self.formula_mode == "preset" and self.formula_type == "cumulative_change":
            value = self._cumulative_change_value(
                model, domain, requests, date_range, date_from, date_to, widget_values
            )
        if value is None:
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        data["value"] = value
        data["value_text"] = self._value_text(value)

        rule_context = {
            "value": value,
            "goal": self.goal_value or 0.0,
            "widget_values": widget_values or {},
            "shifts": self._shift_values(model, requests, date_range, date_from, date_to, widget_values),
        }
        data["status"], data["status_source"], data["status_message"] = self._evaluate_rules(
            rule_context
        )

        if self.show_delta:
            self._fill_delta(data, model, requests, value, date_range, date_from, date_to, widget_values)

    def _fill_delta(self, data, model, requests, value, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Fill the KPI delta against the basis period chosen by the designer."""
        self.ensure_one()
        previous_domain = self._build_domain(date_range, date_from, date_to, shift=self.delta_basis)
        try:
            previous_value = self._value_for(
                model, previous_domain, requests, date_range, date_from, date_to, widget_values, shift=self.delta_basis
            )
        except (UserError, ValidationError) as error:
            _logger.info("Delta of widget %s could not be computed: %s", self.id, error)
            return
        if previous_value is None:
            return
        if previous_value:
            data["delta"] = round((value - previous_value) / previous_value * 100, 1)
        elif value:
            data["delta"] = 100.0
        else:
            # Both periods are empty: there is nothing to compare, so no delta
            # is shown rather than a misleading flat 0%.
            data["delta"] = None

    def _fill_chart_data(self, data, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        groupby_spec = self._groupby_spec()
        if not groupby_spec:
            data["message"] = _("Choose a group by field for this chart.")
            return
        if self._needs_bounded_period() and not self._run_rate_days(date_range, date_from, date_to):
            data["message"] = _("Choose a date field and a bounded period to compute this formula.")
            return

        aggregates = [request[2] for request in requests]
        limit = self.limit if self.limit > 0 else None
        if self.widget_type == "line":
            # A line chart is a trend: take the most recent buckets, then
            # present them in chronological order.
            rows = model._read_group(
                domain,
                [groupby_spec],
                aggregates,
                order="%s desc" % groupby_spec,
                limit=limit,
            )
        else:
            rows = model._read_group(
                domain,
                [groupby_spec],
                aggregates,
                order="%s desc" % aggregates[0],
                limit=limit,
            )

        extra = self._formula_extra(
            model, domain, requests, date_range, date_from, date_to, widget_values, share=False
        )
        contexts = [self._formula_context(row, requests) for row in rows]
        if self._uses_share():
            # In a chart the share of a bucket is measured against the total of
            # every displayed bucket, not against the whole domain, so the
            # domain total is not read at all here.
            extra["total_a"] = sum(context.get("a", 0.0) for context in contexts)

        series = []
        statuses = []
        for row, context in zip(rows, contexts):
            context.update(extra)
            value = self._evaluate_value(context)
            status, source, message = self._evaluate_rules(
                self._bucket_rule_context(value, widget_values)
            )
            series.append(
                {
                    "label": self._group_label(row[0]),
                    "value": value,
                    "status": status,
                    "color": STATUS_COLORS.get(status, STATUS_COLORS["grey"]),
                    "message": message,
                }
            )
            statuses.append((status, source, message))
        if self.widget_type == "line":
            series.reverse()
        if self.formula_mode == "preset" and self.formula_type == "cumulative_change":
            series = self._cumulative_series(series)

        data["series"] = series
        self._apply_bucket_status(data, statuses)
        if series:
            data["value"] = series[-1]["value"]
            data["value_text"] = self._value_text(data["value"])
        else:
            data["message"] = _("No data for the selected period.")

    def _fill_list_data(self, data, model, domain):
        measure_field = False
        if self.measure_key and self.measure_key != "__count":
            field = model._fields.get(self.measure_key)
            if field and field.type in ("float", "integer", "monetary"):
                measure_field = self.measure_key
        limit = self.limit if self.limit > 0 else 10
        records = model.search(
            domain,
            limit=limit,
            order="%s desc" % measure_field if measure_field else "id desc",
        )
        rows = []
        statuses = []
        for record in records:
            value = None
            if measure_field:
                value = self._to_number(record[measure_field])
            status, source, message = self._evaluate_rules(
                self._bucket_rule_context(value)
            )
            rows.append(
                {
                    "id": record.id,
                    "label": record.display_name,
                    "value": value,
                    "status": status,
                    "color": STATUS_COLORS.get(status, STATUS_COLORS["grey"]),
                    "message": message,
                    "extra": self._record_extra(record),
                }
            )
            statuses.append((status, source, message))
        data["rows"] = rows
        self._apply_bucket_status(data, statuses)
        if not rows:
            data["message"] = _("No record matches the selected filters.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _groupby_spec(self):
        self.ensure_one()
        if not self.groupby_key:
            return False
        field = self.source_id._groupby_field(self.groupby_key)
        if not field:
            return False
        if field.granularity:
            return "%s:%s" % (field.field_name, field.granularity)
        return field.field_name

    # ------------------------------------------------------------------
    # Formula helpers
    # ------------------------------------------------------------------
    def _formula_slot_map(self):
        """Return the slot -> measure / weight mapping stored on the widget.

        A preset / custom expression only uses the reserved slot names
        (``a``-``e``, ``w1``, ``w2``); a library formula names its slots
        itself, so any identifier is accepted in that mode. A slot value is
        either a measure key (string), a literal weight (number) or a
        cross-source descriptor (``{"source_id": ..., "measure_key": ...}``).
        """
        self.ensure_one()
        raw = (self.formula_slots or "").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        if self.formula_mode == "library":
            allowed = {str(key) for key in parsed if str(key).isidentifier()}
        else:
            allowed = set(formula_tools.ALL_SLOT_KEYS)
        return {
            str(key): value
            for key, value in parsed.items()
            if key in allowed and value not in (None, "")
        }

    def _slot_source(self, bound):
        """Return the data source a cross-source slot reads, or an empty recordset."""
        self.ensure_one()
        if not isinstance(bound, dict):
            return self.env["od19.dashboard.source"]
        return self.env["od19.dashboard.source"].browse(bound.get("source_id") or 0).exists()

    def _external_slot_values(self):
        """Return the value of every slot bound to another source (cross-source).

        The measure is read on the target model without any widget domain: a
        value crossing models is not tied to the period of this widget. A slot
        whose source or measure has become unavailable is simply skipped, so
        the value resolves to the ``0.0`` default set by ``_formula_context``.
        """
        self.ensure_one()
        values = {}
        for slot_key, bound in self._formula_slot_map().items():
            if not isinstance(bound, dict):
                continue
            source = self._slot_source(bound)
            measure_key = bound.get("measure_key")
            if not source or not source.model_name or source.model_name not in self.env:
                continue
            spec = source._aggregate_spec(measure_key)
            if not spec:
                continue
            try:
                model = self.env[source.model_name]
                model.check_access("read")
                rows = model._read_group([], [], [spec], limit=1)
            except (AccessError, UserError):
                continue
            values[slot_key] = self._to_number(rows[0][0]) if rows and rows[0] else 0.0
        return values

    def _source_measure_keys(self):
        """Return every measure name the whitelist exposes for this source."""
        self.ensure_one()
        keys = {"__count", formula_tools.COUNT_ALIAS}
        keys.update(
            self.source_id.field_ids.filtered(
                lambda field: field.kind == "measure"
            ).mapped("field_name")
        )
        return keys

    def _effective_expression(self):
        """Return the expression actually evaluated for this widget."""
        self.ensure_one()
        if self.formula_mode == "measure":
            return "value"
        if self.formula_mode == "preset":
            if not self.formula_type:
                return "0"
            return formula_tools.build_preset_expression(
                self.formula_type, self._formula_slot_map()
            )
        if self.formula_mode == "library":
            return (self.formula_id.expression or "").strip() or "0"
        return (self.formula_expression or "").strip()

    def _allowed_names(self):
        """Return every name a custom expression of this widget may reference."""
        self.ensure_one()
        names = set(formula_tools.ALL_SLOT_KEYS)
        names |= set(formula_tools.IMPLICIT_NAMES)
        names -= {"__count"}
        names |= {key for key in self._source_measure_keys() if key != "__count"}
        names |= set(self._formula_slot_map())
        names |= {"widget_%s" % widget_id for widget_id in self._dependency_ids()}
        return names

    def _aggregate_requests(self):
        """Return the de-duplicated ``(alias, measure_key, spec)`` triples to read.

        The list is ordered consistently with the aggregate columns returned
        by a single ``_read_group`` call. A KPI, a delta and a period
        comparison read a single row without any grouping, so the offset of
        the first aggregate in a result row is derived from the length of the
        row instead of assuming a group value is always present.
        """
        self.ensure_one()
        source = self.source_id
        requests = []
        seen = set()

        def add(alias, measure_key):
            if not measure_key:
                return
            spec = source._aggregate_spec(measure_key)
            if not spec:
                return
            key = (alias, spec)
            if key in seen:
                return
            seen.add(key)
            requests.append((alias, measure_key, spec))

        if self.formula_mode == "measure":
            add("value", self.measure_key or "__count")
            return requests

        if self.formula_mode == "preset":
            slots = self._formula_slot_map()
            for slot_key in formula_tools.SLOT_KEYS:
                measure_key = slots.get(slot_key)
                if isinstance(measure_key, str):
                    add(slot_key, measure_key)
            return requests

        # Custom and library modes: the names actually written in the
        # expression are resolved one by one — a slot name maps to the measure
        # (or weight) bound to it, count_records maps to the record count, any
        # other name is a measure field of the whitelisted source. A slot bound
        # to another source (a dict) is not read here: it is resolved by
        # ``_external_slot_values()``.
        slots = self._formula_slot_map()
        measure_keys = self._source_measure_keys()
        for name in sorted(formula_tools.expression_names(self._effective_expression())):
            if name in formula_tools.WEIGHT_KEYS:
                continue
            if name in slots:
                measure_key = slots.get(name)
            elif name == formula_tools.COUNT_ALIAS:
                measure_key = "__count"
            elif name in measure_keys:
                measure_key = name
            else:
                continue
            if isinstance(measure_key, str):
                add(name, measure_key)
        if not requests:
            # A custom formula may name only other widgets or literals: it still
            # needs one aggregate column so the widget can be read at all. The
            # alias is internal — the expression never names it — so it is kept
            # out of the operand list shown by the builder.
            add("value", self.measure_key or "__count")
        return requests

    def _dependency_ids(self):
        """Return the ids of the other widgets this widget reads.

        A dependency comes from a status rule comparing with another widget and
        from a ``widget_<id>`` name written in a custom expression.
        """
        self.ensure_one()
        ids = set(self.rule_ids.filtered("active").mapped("compare_widget_id").ids)
        for name in formula_tools.expression_names(self._effective_expression()):
            if not name.startswith("widget_"):
                continue
            suffix = name[len("widget_") :]
            if suffix.isdigit():
                ids.add(int(suffix))
        ids.discard(self.id)
        return sorted(ids)

    def _unresolved_names(self):
        """Return the expression names that would have no value at read time."""
        self.ensure_one()
        available = set(formula_tools.IMPLICIT_NAMES)
        # A bound slot always carries a value: a string is a measure key read
        # from the source, a number is a literal weight (``w1`` / ``w2`` of the
        # weighted average) taken from the widget itself.
        available |= set(self._formula_slot_map())
        available |= {"widget_%s" % widget_id for widget_id in self._dependency_ids()}
        available |= {key for key in self._source_measure_keys() if key != "__count"}
        used = formula_tools.expression_names(self._effective_expression())
        return sorted(name for name in used if name not in available)

    def _validate_formula_config(self):
        """Validate the whole formula configuration and raise ``ValidationError``.

        Called automatically by the ``_check_formula_config`` constraint on
        every create / write of a widget, and explicitly by ``preview_widget``
        because a record built with ``Model.new()`` never triggers a constraint.
        """
        for widget in self:
            widget._validate_visible_expression()
            if widget.formula_mode == "measure":
                continue
            expression = widget._effective_expression()
            if widget.formula_mode == "preset":
                if not widget.formula_type:
                    raise ValidationError(_("Choose a preset formula."))
                missing = [
                    slot_key
                    for slot_key in formula_tools.PRESET_REQUIRED_SLOTS.get(
                        widget.formula_type, ()
                    )
                    if slot_key not in widget._formula_slot_map()
                ]
                if missing:
                    raise ValidationError(
                        _("The preset formula '%(formula)s' needs the slot(s): %(slots)s.")
                        % {"formula": widget.formula_type, "slots": ", ".join(missing)}
                    )
            elif widget.formula_mode == "library":
                if not widget.formula_id:
                    raise ValidationError(
                        _("Choose a formula from the library for widget '%s'.") % widget.name
                    )
            elif widget.formula_mode == "custom":
                if not (widget.formula_expression or "").strip():
                    raise ValidationError(_("Type the formula of this widget."))
            available_measures = widget._source_measure_keys()
            unknown_slots = []
            for slot_key, value in widget._formula_slot_map().items():
                if isinstance(value, str):
                    if value not in available_measures:
                        unknown_slots.append(slot_key)
                elif isinstance(value, dict):
                    # A cross-source slot: the measure belongs to the target
                    # source, not to the source of this widget.
                    source = widget._slot_source(value)
                    measure_key = value.get("measure_key")
                    if not source or not source._aggregate_spec(measure_key):
                        unknown_slots.append(slot_key)
            if unknown_slots:
                raise ValidationError(
                    _("The slot(s) %s are bound to a field the data source does not offer.")
                    % ", ".join(sorted(unknown_slots))
                )
            formula_tools.validate_expression(expression, widget._allowed_names())
            unresolved = widget._unresolved_names()
            if unresolved:
                raise ValidationError(
                    _("The formula uses names without value: %s.") % ", ".join(unresolved)
                )

    def _validate_visible_expression(self):
        """Validate ``visible_expression`` of this widget (spec phase 2, 3.3).

        The condition is evaluated with the same names as the formula plus the
        widget value, so ``_allowed_names()`` is the whitelist.
        """
        self.ensure_one()
        expression = (self.visible_expression or "").strip()
        if not expression:
            return
        allowed = self._allowed_names() | {"value"}
        formula_tools.validate_expression(expression, allowed)
        unresolved = sorted(
            name
            for name in formula_tools.expression_names(expression)
            if name not in allowed
        )
        if unresolved:
            raise ValidationError(
                _("The visibility condition uses names without value: %s.")
                % ", ".join(unresolved)
            )

    # ------------------------------------------------------------------
    # Formula evaluation
    # ------------------------------------------------------------------
    def _shifted_period(self, date_range=None, date_from=None, date_to=None, shift=None):
        """Return the ``(start, end)`` dates of a period, or ``(None, None)``."""
        self.ensure_one()
        start, end, _field_type = self._period_bounds(date_range, date_from, date_to, shift)
        return start, end

    def _run_rate_days(self, date_range=None, date_from=None, date_to=None, shift=None):
        """Return ``(days_in_period, days_elapsed)``, or ``None`` without a bound."""
        self.ensure_one()
        if not self.date_key:
            return None
        start, end = self._shifted_period(date_range, date_from, date_to, shift)
        if not start or not end:
            return None
        days_in_period = (end - start).days + 1
        elapsed_end = min(end, fields.Date.context_today(self))
        days_elapsed = max((elapsed_end - start).days + 1, 0)
        if days_elapsed <= 0:
            return None
        return days_in_period, days_elapsed

    def _needs_bounded_period(self):
        """Return True when the formula needs a bounded period to be computable."""
        self.ensure_one()
        return bool(
            formula_tools.expression_names(self._effective_expression())
            & {"days_in_period", "days_elapsed"}
        )

    def _uses_share(self):
        """Return True when the expression divides a measure by the total of A."""
        self.ensure_one()
        return "total_a" in formula_tools.expression_names(self._effective_expression())

    def _formula_context(self, row, requests, extra=None):
        """Return the ``safe_eval`` context of one ``_read_group`` row.

        A ``_read_group`` row is flat: the group by values come first, then the
        aggregate of every request. The alias of each request becomes a name of
        the context. A KPI, a delta and a period comparison read a single row
        without any grouping, so their row starts directly with the aggregates:
        the offset is derived from the length of the row instead of assuming a
        group value is always present. Every implicit name is pre-set to
        ``0.0`` so an expression can never raise ``KeyError`` at evaluation.
        """
        self.ensure_one()
        offset = max(len(row) - len(requests), 0)
        context = {}
        for index, (alias, _measure_key, _spec) in enumerate(requests):
            value = row[index + offset] if len(row) > index + offset else 0
            context[alias] = self._to_number(value)
        # A slot bound to a literal weight (``w1`` / ``w2`` of the weighted
        # average) is not an aggregate: its value is the number stored on the
        # widget itself.
        for slot_key, slot_value in self._formula_slot_map().items():
            if not isinstance(slot_value, str):
                context.setdefault(slot_key, self._to_number(slot_value))
        for name in formula_tools.IMPLICIT_NAMES:
            context.setdefault(name, 0.0)
        for widget_id in self._dependency_ids():
            context.setdefault("widget_%s" % widget_id, 0.0)
        context["goal"] = self.goal_value or 0.0
        context.update(extra or {})
        return context

    def _formula_extra(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None, *, shift=None, share=True):
        """Return the context values that are not read from a single aggregate row.

        ``share=False`` skips the domain total read (used by charts, which
        measure the share against their displayed buckets); ``shift`` is the
        reference period the values are read on.
        """
        self.ensure_one()
        extra = self._external_slot_values()
        for widget_id in self._dependency_ids():
            extra["widget_%s" % widget_id] = self._to_number((widget_values or {}).get(widget_id))
        if share and self._uses_share():
            slot_a = self._formula_slot_map().get("a") or self.measure_key
            spec = self.source_id._aggregate_spec(slot_a) if isinstance(slot_a, str) else False
            if spec:
                rows = model._read_group(domain, [], [spec], limit=1)
                extra["total_a"] = self._to_number(rows[0][0]) if rows and rows[0] else 0.0
        if self._needs_bounded_period():
            days = self._run_rate_days(date_range, date_from, date_to, shift=shift)
            if days:
                extra["days_in_period"] = float(days[0])
                extra["days_elapsed"] = float(days[1])
        return extra

    def _visibility_context(self, data, widget_values=None):
        """Return the context used to evaluate ``visible_expression``.

        The condition sees the widget value, the goal, the number of records,
        every operand read for the widget, the values of the widgets it reads
        and the cross-source slot values — the same names a formula may use
        plus ``value`` (spec phase 2, 3.3).
        """
        self.ensure_one()
        context = {
            "value": data.get("value"),
            "goal": self.goal_value or 0.0,
            "record_count": data.get("record_count") or 0,
        }
        for name in formula_tools.IMPLICIT_NAMES:
            context.setdefault(name, 0.0)
        context[formula_tools.COUNT_ALIAS] = data.get("record_count") or 0
        for operand in data.get("operands") or []:
            context[operand["alias"]] = operand["value"]
        for widget_id in self._dependency_ids():
            context["widget_%s" % widget_id] = self._to_number(
                (widget_values or {}).get(widget_id)
            )
        context.update(self._external_slot_values())
        return context

    def _is_visible(self, context):
        """Return False when ``visible_expression`` evaluates to a falsy value.

        An empty condition keeps the widget visible (historical behaviour). A
        condition that cannot be evaluated fails open, so a broken condition
        never hides a widget silently.
        """
        self.ensure_one()
        expression = (self.visible_expression or "").strip()
        if not expression:
            return True
        try:
            return bool(formula_tools.evaluate_expression(expression, context))
        except (ArithmeticError, ValueError, TypeError, NameError):
            return True

    def _evaluate_value(self, context):
        """Evaluate the effective expression on ``context``.

        A division by zero and a malformed or unresolvable expression raise a
        ``UserError``; any other failure is left to the caller, which logs it
        and fails the widget soft.
        """
        self.ensure_one()
        expression = self._effective_expression()
        if not expression:
            raise UserError(_("Type the formula of this widget."))
        if expression == "value":
            return context.get("value", 0.0)
        try:
            return formula_tools.evaluate_expression(expression, context)
        except ZeroDivisionError as error:
            raise UserError(
                _("The formula of widget '%s' divides by zero for this period.") % self.name
            ) from error
        except (ArithmeticError, ValueError, TypeError, NameError) as error:
            raise UserError(
                _("The formula of widget '%s' could not be evaluated: %s") % (self.name, error)
            ) from error

    def _record_count(self, model, domain):
        """Return the number of records the widget would collect on ``domain``."""
        self.ensure_one()
        rows = model._read_group(domain, [], ["__count"], limit=1)
        return int(rows[0][0] or 0) if rows and rows[0] else 0

    def _operand_details(self, requests, context):
        """Return the ``alias`` → label / value list shown by the builder preview."""
        self.ensure_one()
        labels = {
            field.field_name: field.label or field.field_name
            for field in self.source_id.field_ids
        }
        details = []
        used = formula_tools.expression_names(self._effective_expression())
        for alias, measure_key, _spec in requests:
            if alias not in used and alias not in formula_tools.SLOT_KEYS:
                # The aggregate column read only so the widget has a row: the
                # formula names neither this alias nor a slot, so it is not an
                # operand the designer wrote.
                continue
            if measure_key == "__count":
                label = _("Number of records")
            else:
                label = labels.get(measure_key, measure_key)
            details.append(
                {"alias": alias, "label": label, "value": context.get(alias, 0.0)}
            )
        for name in ("total_a", "days_in_period", "days_elapsed"):
            if name in used:
                details.append(
                    {"alias": name, "label": name, "value": context.get(name, 0.0)}
                )
        return details

    def _number_text(self, value, decimals):
        """Format a number the way the dashboard client does (no padding zeros)."""
        text = ("%%.%df" % decimals) % self._to_number(value)
        sign = "-" if text.startswith("-") else ""
        integer, _dot, decimal = (text[1:] if sign else text).partition(".")
        grouped = "{:,}".format(int(integer or 0))
        return "%s%s%s" % (
            sign,
            grouped,
            (".%s" % decimal.rstrip("0")) if decimal.rstrip("0") else "",
        )

    def _value_text(self, value):
        """Return the value formatted with ``value_format``, mirroring the client."""
        self.ensure_one()
        if value is None:
            return ""
        currency = self.env.company.currency_id
        if self.value_format == "percent":
            return "%s%%" % self._number_text(value, 1)
        if self.value_format == "hours":
            return "%s h" % self._number_text(value, 1)
        if self.value_format == "currency":
            text = self._number_text(value, currency.decimal_places or 2)
            symbol = currency.symbol or ""
            if not symbol:
                return text
            if currency.position == "after":
                return "%s %s" % (text, symbol)
            return "%s %s" % (symbol, text)
        return self._number_text(value, 2)

    def _value_for(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None, shift=None):
        """Evaluate the formula of this widget on an arbitrary domain."""
        self.ensure_one()
        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [], aggregates, limit=1)
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values, shift=shift)
        return self._evaluate_value(self._formula_context(rows[0] if rows else (), requests, extra))

    def _shift_values(self, model, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Return ``{shift: value}`` for the shifts the status rules of this widget need."""
        self.ensure_one()
        values = {}
        for shift in sorted(self._required_shifts()):
            domain = self._build_domain(date_range, date_from, date_to, shift=shift)
            try:
                values[shift] = self._value_for(
                    model, domain, requests, date_range, date_from, date_to, widget_values, shift=shift
                )
            except (UserError, ValidationError) as error:
                # A rule comparing with an unreachable period is skipped, not fatal.
                _logger.info("Shift '%s' of widget %s could not be computed: %s", shift, self.id, error)
                values[shift] = None
        return values

    def _cumulative_series(self, series):
        """Turn a series into its cumulative change (bucket − first bucket)."""
        if not series:
            return series
        base = series[0]["value"]
        changed = []
        for item in series:
            new_item = dict(item)
            new_item["value"] = round(item["value"] - base, 4)
            changed.append(new_item)
        return changed

    def _cumulative_change_value(self, model, domain, requests, date_range=None, date_from=None, date_to=None, widget_values=None):
        """Return the change between the first and the last bucket of the period.

        Used when ``cumulative_change`` is applied to a widget without buckets
        (KPI or list): the period of the widget is bucketed by month on its date
        field, each bucket is evaluated with the formula and the difference
        between the last and the first bucket is returned. ``None`` means the
        widget has no date field, so the formula cannot be computed.
        """
        self.ensure_one()
        if not self.date_key:
            return None
        groupby_spec = "%s:month" % self.date_key
        aggregates = [request[2] for request in requests]
        rows = model._read_group(domain, [groupby_spec], aggregates, order="%s asc" % groupby_spec)
        if len(rows) < 2:
            return 0.0
        extra = self._formula_extra(model, domain, requests, date_range, date_from, date_to, widget_values)
        values = [
            self._evaluate_value(self._formula_context(row, requests, extra))
            for row in rows
        ]
        return values[-1] - values[0]

    # ------------------------------------------------------------------
    # Status rules
    # ------------------------------------------------------------------
    def _required_shifts(self):
        """Return the shifted periods this widget needs to read.

        Derived from the period comparison of the KPI (``delta_basis``), from
        the reference period of growth / cumulative change formulas
        (``formula_basis``) and from the status rules comparing a period.
        """
        self.ensure_one()
        shifts = set()
        if self.show_delta and self.delta_basis:
            shifts.add(self.delta_basis)
        if self.formula_mode in ("preset", "custom", "library") and self.formula_basis:
            shifts.add(self.formula_basis)
        shifts.update(
            self.rule_ids.filtered(
                lambda rule: rule.active
                and rule.compare_type in formula_tools.PERIOD_COMPARE_TYPES
            ).mapped("compare_type")
        )
        return {"previous" if shift == "prev" else shift for shift in shifts}

    def _is_lower_better(self):
        """Infer the direction of the KPI so the delta can be coloured.

        A red rule that triggers on a *high* value means a low value is good
        (``lower is better``); a red rule triggering on a low value means the
        opposite. Defaults to ``higher is better`` when no red rule exists.
        """
        self.ensure_one()
        for rule in self.rule_ids.filtered("active"):
            if rule.status == "red":
                return rule.operator in (">", ">=")
        return False

    def _evaluate_rules(self, context):
        """Return ``(status, status_source, message)`` with a first-match-wins table.

        ``status_source`` is ``"rule"`` when a rule matched and ``"default"``
        when the widget falls back to ``default_status``. ``message`` is the
        ``alert_message`` of the matching rule (empty when no rule matched).
        The left-hand side of every comparison is the value carried by
        ``context`` — the widget value for a KPI, a bucket value for a chart or
        a row value for a list.
        """
        self.ensure_one()
        if context.get("value") is not None:
            for rule in self.rule_ids.filtered("active"):
                operand = rule._compare_operand(context)
                if formula_tools.compare_values(context.get("value"), rule.operator, operand):
                    return rule.status, "rule", rule.alert_message or ""
        return self.default_status, "default", ""

    def _bucket_rule_context(self, value, widget_values=None):
        """Return the rule context of one chart bucket or one list row.

        A bucket has no period of its own, so the shifted values are empty: a
        rule comparing a period simply does not match on a bucket.
        """
        self.ensure_one()
        return {
            "value": value,
            "goal": self.goal_value or 0.0,
            "widget_values": widget_values or {},
            "shifts": {},
        }

    def _apply_bucket_status(self, data, statuses):
        """Set the widget status to the most severe bucket / row status."""
        self.ensure_one()
        if not statuses:
            data["status"], data["status_source"], data["status_message"] = (
                "grey",
                "default",
                "",
            )
            return
        data["status"], data["status_source"], data["status_message"] = max(
            statuses, key=lambda item: STATUS_SEVERITY.get(item[0], 0)
        )

    @api.constrains("formula_mode", "formula_expression", "rule_ids", "active")
    def _check_dependency_cycle(self):
        for widget in self:
            if widget.dashboard_id:
                widget.dashboard_id._check_no_cycle()

    def _build_domain(self, date_range=None, date_from=None, date_to=None, shift=None):
        self.ensure_one()
        domain = []
        raw_domain = (self.domain or "").strip()
        if raw_domain:
            try:
                parsed = safe_eval(raw_domain)
            except Exception as error:  # noqa: BLE001
                raise ValidationError(
                    _("The filter of widget '%s' is not valid: %s") % (self.name, error)
                ) from error
            if not isinstance(parsed, list):
                raise ValidationError(
                    _("The filter of widget '%s' must be a list (Odoo domain).") % self.name
                )
            domain += parsed

        effective_range = date_range or self.date_range or "all_time"
        if self.date_key and (effective_range != "all_time" or date_from or date_to):
            domain += self._date_bounds(effective_range, date_from, date_to, shift)
        return domain

    def _period_bounds(self, date_range=None, date_from=None, date_to=None, shift=None):
        """Return the ``(start, end)`` dates of the period the widget reads.

        ``shift`` moves the window back in time: ``previous`` (same length),
        ``yty`` (same period last year), ``mtm`` (previous month) or ``qtq``
        (previous quarter). ``(None, None, field_type)`` means "no date bound",
        which is the case for ``all_time`` and for a widget without a date
        field. Always returns three values, so the caller can unpack
        ``start, end, field_type`` without a special case.
        """
        self.ensure_one()
        field_type = "date"
        if self.date_key and self.source_id.model_name in self.env:
            field = self.env[self.source_id.model_name]._fields.get(self.date_key)
            field_type = field.type if field else "date"
        if not self.date_key:
            return None, None, field_type
        effective_range = date_range or self.date_range or "all_time"

        today = fields.Date.context_today(self)

        start = end = None
        if date_from or date_to:
            start = fields.Date.to_date(date_from) if date_from else None
            end = fields.Date.to_date(date_to) if date_to else None
        elif effective_range == "all_time":
            return None, None, field_type
        elif effective_range == "today":
            start = end = today
        elif effective_range == "yesterday":
            start = end = today - timedelta(days=1)
        elif effective_range == "last_7_days":
            start, end = today - timedelta(days=6), today
        elif effective_range == "last_30_days":
            start, end = today - timedelta(days=29), today
        elif effective_range == "last_90_days":
            start, end = today - timedelta(days=89), today
        elif effective_range == "this_month":
            start, end = today.replace(day=1), today
        elif effective_range == "this_quarter":
            start, end = today.replace(month=3 * ((today.month - 1) // 3) + 1, day=1), today
        elif effective_range == "this_year":
            start, end = today.replace(month=1, day=1), today
        elif effective_range == "next_7_days":
            start, end = today, today + timedelta(days=7)
        elif effective_range == "overdue":
            start, end = None, today - timedelta(days=1)
        else:
            return None, None, field_type

        if shift:
            start, end = formula_tools.apply_shift(start, end, shift)
        return start, end, field_type

    def _date_bounds(self, range_key, date_from, date_to, shift=None):
        self.ensure_one()
        start, end, field_type = self._period_bounds(range_key, date_from, date_to, shift)
        bounds = []
        if field_type == "date":
            if start:
                bounds.append((self.date_key, ">=", start.isoformat()))
            if end:
                bounds.append((self.date_key, "<=", end.isoformat()))
            return bounds
        if start:
            bounds.append((self.date_key, ">=", "%s 00:00:00" % start.isoformat()))
        if end:
            bounds.append((self.date_key, "<=", "%s 23:59:59" % end.isoformat()))
        return bounds

    def _group_label(self, group_value):
        self.ensure_one()
        key_parts = (self.groupby_key or "").split(":")
        field_name = key_parts[0]
        granularity = key_parts[1] if len(key_parts) > 1 else None
        model = self.env[self.source_id.model_name]
        field = model._fields.get(field_name)
        if group_value is None or group_value is False:
            return _("Undefined")
        if isinstance(group_value, models.BaseModel):
            return group_value.display_name or _("Undefined")
        if granularity in ("month", "quarter", "year") and isinstance(group_value, (date, datetime)):
            value = group_value.date() if isinstance(group_value, datetime) else group_value
            if granularity == "year":
                return format_date(self.env, value, date_format="yyyy")
            if granularity == "month":
                return format_date(self.env, value, date_format="MMMM yyyy")
            return format_date(self.env, value)
        if field is None:
            return str(group_value)
        if field.type == "selection":
            labels = dict(field._description_selection(self.env))
            return labels.get(group_value, str(group_value))
        if field.type == "date":
            return format_date(self.env, group_value)
        if field.type == "datetime":
            return format_datetime(self.env, group_value)
        if field.type == "boolean":
            return _("Yes") if group_value else _("No")
        return str(group_value)

    def _record_extra(self, record):
        if "state" in record._fields:
            labels = dict(record._fields["state"]._description_selection(self.env))
            state = record.state
            return labels.get(state, state)
        return ""

    @api.model
    def _to_number(self, value):
        if value is None or value is False:
            return 0.0
        if isinstance(value, models.BaseModel):
            return float(len(value))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
