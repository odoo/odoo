/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { BuilderDialog } from "./builder_dialog";

const PIE_PALETTE = [
    "#9E2424",
    "#C0562F",
    "#E0A458",
    "#4E8098",
    "#2E5E4E",
    "#6B4E71",
    "#8A8A8A",
];

/**
 * Role based dashboard client action.
 *
 * Renders every widget of the selected dashboard, offers a period selector and
 * exposes the in-browser builder: add / edit / delete widgets, drag to reorder
 * and resize them. All writes go through the ``od19.dashboard`` RPC methods so
 * the server keeps controlling what may be read and edited.
 */
export class DashboardAction extends Component {
    static template = "od19_dashboard.DashboardAction";
    static components = { BuilderDialog };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            dashboards: [],
            dashboardId: null,
            dashboard: null,
            widgets: [],
            meta: {
                sources: [],
                formulas: [],
                widget_types: [],
                value_formats: [],
                formula_modes: [],
                formula_types: [],
                compare_types: [],
                operators: [],
                statuses: [],
                status_colors: {},
                period_bases: [],
                date_ranges: [],
                audiences: [],
                currency: {},
                grid: { min_w: 2, max_w: 12, min_h: 1, max_h: 6 },
            },
            dateRange: "",
            editMode: false,
            builder: { open: false, config: null },
            draft: { open: false, name: "", audience: "management", default_date_range: "last_30_days" },
            dragWidgetId: null,
        });

        onWillStart(async () => {
            await this._loadMeta();
            await this._loadDashboards();
        });
    }

    // ------------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------------
    async _loadMeta() {
        this.state.meta = await this.orm.call("od19.dashboard", "get_builder_meta", []);
    }

    async _loadDashboards() {
        this.state.dashboards = await this.orm.call("od19.dashboard", "get_user_dashboards", []);
        const params = (this.props.action && this.props.action.params) || {};
        let dashboardId = params.dashboard_id || null;
        if (!dashboardId || !this.state.dashboards.some((d) => d.id === dashboardId)) {
            const preferred =
                this.state.dashboards.find((d) => d.is_default) || this.state.dashboards[0];
            dashboardId = preferred ? preferred.id : null;
        }
        this.state.dashboardId = dashboardId;
        if (dashboardId) {
            await this._loadDashboard();
        } else {
            this.state.loading = false;
        }
    }

    async _loadDashboard() {
        if (!this.state.dashboardId) {
            this.state.dashboard = null;
            this.state.widgets = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const data = await this.orm.call("od19.dashboard", "get_dashboard_data", [
            this.state.dashboardId,
            this.state.dateRange || null,
        ]);
        this.state.dashboard = data.dashboard;
        this.state.widgets = this._decorate(data.widgets);
        this.state.editMode = false;
        this.state.loading = false;
    }

    async _reloadWidgets() {
        const data = await this.orm.call("od19.dashboard", "get_dashboard_data", [
            this.state.dashboardId,
            this.state.dateRange || null,
        ]);
        this.state.dashboard = data.dashboard;
        this.state.widgets = this._decorate(data.widgets);
    }

    // ------------------------------------------------------------------
    // Header actions
    // ------------------------------------------------------------------
    async onSelectDashboard(ev) {
        const id = parseInt(ev.target.value, 10);
        // The <select> is bound with t-model, so ``state.dashboardId`` may
        // already hold the new value: compare with the dashboard actually
        // loaded to avoid skipping the reload.
        const loadedId = this.state.dashboard ? this.state.dashboard.id : null;
        if (!id || id === loadedId) {
            return;
        }
        this.state.dashboardId = id;
        this.state.dateRange = "";
        await this._loadDashboard();
    }

    async onSelectDateRange(ev) {
        this.state.dateRange = ev.target.value;
        await this._reloadWidgets();
    }

    async onRefresh() {
        await this._reloadWidgets();
    }

    toggleEditMode() {
        if (!this.state.dashboard || !this.state.dashboard.can_edit) {
            return;
        }
        this.state.editMode = !this.state.editMode;
    }

    // ------------------------------------------------------------------
    // Builder: widgets
    // ------------------------------------------------------------------
    openCreateWidget() {
        this.state.builder = { open: true, config: null };
    }

    openEditWidget(widget) {
        const config = { ...widget.config };
        // ``config.formula_expression`` is the *effective* expression, not the
        // stored field: a measure widget carries the internal alias "value".
        // Only a custom formula has a real expression worth hydrating.
        if (config.formula_mode !== "custom") {
            config.formula_expression = "";
        }
        this.state.builder = { open: true, config };
    }

    closeBuilder() {
        this.state.builder = { open: false, config: null };
    }

    async onBuilderSave(values) {
        const config = this.state.builder.config;
        try {
            if (config && config.id) {
                await this.orm.call("od19.dashboard", "update_widget", [config.id, values]);
            } else {
                await this.orm.call("od19.dashboard", "create_widget", [this.state.dashboardId, values]);
            }
            this.closeBuilder();
            await this._reloadWidgets();
        } catch (error) {
            this._notifyError(error);
        }
    }

    async onDeleteWidget(widget) {
        this.env.services.dialog.add(ConfirmationDialog, {
            body: _t("Remove the widget “%s” from this dashboard?", widget.name),
            confirm: () => this._deleteWidget(widget),
        });
    }

    async _deleteWidget(widget) {
        try {
            await this.orm.call("od19.dashboard", "delete_widget", [widget.id]);
            await this._reloadWidgets();
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // Drag & drop / resize
    // ------------------------------------------------------------------
    onDragStart(ev, widget) {
        if (!this.state.editMode) {
            return;
        }
        this.state.dragWidgetId = widget.id;
        if (ev.dataTransfer) {
            ev.dataTransfer.effectAllowed = "move";
            ev.dataTransfer.setData("text/plain", String(widget.id));
        }
    }

    onDragOver(ev) {
        if (this.state.editMode) {
            ev.preventDefault();
        }
    }

    async onDrop(ev, target) {
        if (!this.state.editMode) {
            return;
        }
        ev.preventDefault();
        const sourceId = this.state.dragWidgetId;
        this.state.dragWidgetId = null;
        if (!sourceId || sourceId === target.id) {
            return;
        }
        const widgets = [...this.state.widgets];
        const from = widgets.findIndex((w) => w.id === sourceId);
        const to = widgets.findIndex((w) => w.id === target.id);
        if (from < 0 || to < 0) {
            return;
        }
        const [moved] = widgets.splice(from, 1);
        widgets.splice(to, 0, moved);
        widgets.forEach((widget, index) => {
            widget.sequence = (index + 1) * 10;
        });
        this.state.widgets = widgets;
        await this._saveLayout();
    }

    async resizeWidget(widget, deltaW, deltaH) {
        const grid = this.state.meta.grid || {};
        const width = Math.min(grid.max_w, Math.max(grid.min_w, (widget.grid_w || 4) + deltaW));
        const height = Math.min(grid.max_h, Math.max(grid.min_h, (widget.grid_h || 2) + deltaH));
        if (width === widget.grid_w && height === widget.grid_h) {
            return;
        }
        widget.grid_w = width;
        widget.grid_h = height;
        await this._saveLayout();
    }

    async _saveLayout() {
        const layout = this.state.widgets.map((widget) => ({
            id: widget.id,
            sequence: widget.sequence,
            grid_w: widget.grid_w,
            grid_h: widget.grid_h,
        }));
        try {
            await this.orm.call("od19.dashboard", "save_layout", [this.state.dashboardId, layout]);
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // Builder: dashboards
    // ------------------------------------------------------------------
    openCreateDashboard() {
        const audiences = this.state.meta.audiences || [];
        this.state.draft = {
            open: true,
            name: "",
            audience: audiences.length ? audiences[0].key : "management",
            default_date_range: "last_30_days",
        };
    }

    closeCreateDashboard() {
        this.state.draft.open = false;
    }

    async confirmCreateDashboard() {
        const draft = this.state.draft;
        if (!draft.name.trim()) {
            this._notifyError(_t("Give the dashboard a name."));
            return;
        }
        try {
            const id = await this.orm.create("od19.dashboard", [
                {
                    name: draft.name.trim(),
                    audience: draft.audience,
                    default_date_range: draft.default_date_range,
                },
            ]);
            this._notify(_t("Dashboard created. Use “Add Widget” to design it."));
            this.state.draft.open = false;
            this.state.dashboards = await this.orm.call("od19.dashboard", "get_user_dashboards", []);
            this.state.dashboardId = id[0];
            this.state.dateRange = "";
            await this._loadDashboard();
            this.state.editMode = true;
        } catch (error) {
            this._notifyError(error);
        }
    }

    async duplicateDashboard() {
        if (!this.state.dashboardId) {
            return;
        }
        try {
            const newId = await this.orm.call("od19.dashboard", "duplicate_dashboard", [
                this.state.dashboardId,
            ]);
            this.state.dashboards = await this.orm.call("od19.dashboard", "get_user_dashboards", []);
            this.state.dashboardId = newId;
            this.state.dateRange = "";
            await this._loadDashboard();
            this.state.editMode = true;
        } catch (error) {
            this._notifyError(error);
        }
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------
    get audienceLabel() {
        if (!this.state.dashboard) {
            return "";
        }
        const match = (this.state.meta.audiences || []).find(
            (a) => a.key === this.state.dashboard.audience
        );
        return match ? match.label : this.state.dashboard.audience;
    }

    _decorate(widgets) {
        for (const widget of widgets) {
            widget.value_text = this._format(widget.value, widget.value_format);
            widget.goal_text = widget.goal_value
                ? this._format(widget.goal_value, widget.value_format)
                : "";
            widget.delta_text =
                widget.delta === null || widget.delta === undefined
                    ? ""
                    : `${widget.delta > 0 ? "+" : ""}${widget.delta}%`;
            widget.delta_class = this._deltaClass(widget);
            widget.delta_icon = this._deltaIcon(widget);
            widget.delta_note = this._basisLabel(widget.delta_basis).toLowerCase();
            // Shown as a tooltip on the widget card while designing.
            widget.formula_hint = widget.formula_expression || "";
            widget.progress =
                widget.goal_value > 0 && widget.value !== null
                    ? Math.min(100, Math.round((widget.value / widget.goal_value) * 100))
                    : null;
            // Phase 2: the visibility condition may hide the widget, and the
            // rule that decided the colour may carry an alert message.
            widget.hidden = widget.visible === false;
            widget.alert_text = widget.status_message || "";
            if (widget.widget_type === "bar") {
                widget.bars = this._bars(widget);
            } else if (widget.widget_type === "line") {
                widget.line = this._line(widget);
            } else if (widget.widget_type === "pie") {
                widget.slices = this._slices(widget);
            }
        }
        return widgets;
    }

    _deltaClass(widget) {
        if (!widget.delta) {
            return "od19-delta-flat";
        }
        const positive = widget.delta > 0;
        // The server infers the direction from the first red rule, so a widget
        // whose alert is "below a threshold" is not shown as improving.
        const better = widget.is_lower_better ? !positive : positive;
        return better ? "od19-delta-good" : "od19-delta-bad";
    }

    // Raw direction of the change (independent from "better / worse").
    _deltaIcon(widget) {
        if (!widget.delta) {
            return "fa-minus";
        }
        return widget.delta > 0 ? "fa-arrow-up" : "fa-arrow-down";
    }

    _basisLabel(basis) {
        const match = (this.state.meta.period_bases || []).find((item) => item.key === basis);
        return match ? match.label : _t("previous period");
    }

    _bars(widget) {
        const series = widget.series || [];
        const max = Math.max(0, ...series.map((item) => Math.abs(item.value)));
        const factor = max || 1;
        return series.map((item) => ({
            label: item.label,
            text: this._format(item.value, widget.value_format),
            width: Math.round((Math.abs(item.value) / factor) * 100),
            // Conditional formatting: the server decides the colour of a bucket.
            color: item.color || "",
            status: item.status || "",
            message: item.message || "",
        }));
    }

    _line(widget) {
        const series = widget.series || [];
        if (!series.length) {
            return { points: "", dots: [] };
        }
        const values = series.map((item) => item.value);
        const max = Math.max(...values, 0);
        const min = Math.min(...values, 0);
        const span = max - min || 1;
        const step = series.length > 1 ? 100 / (series.length - 1) : 0;
        const dots = series.map((item, index) => ({
            key: `${item.label}-${index}`,
            x: (index * step).toFixed(2),
            y: (38 - ((item.value - min) / span) * 34).toFixed(2),
            label: item.label,
            text: this._format(item.value, widget.value_format),
            color: item.color || "",
            status: item.status || "",
            message: item.message || "",
        }));
        return {
            points: dots.map((dot) => `${dot.x},${dot.y}`).join(" "),
            dots,
        };
    }

    _slices(widget) {
        const series = widget.series || [];
        const total = series.reduce((acc, item) => acc + Math.abs(item.value), 0) || 1;
        let angle = -90;
        return series.map((item, index) => {
            const sweep = (Math.abs(item.value) / total) * 360;
            const start = angle;
            const end = angle + sweep;
            angle = end;
            const [x1, y1] = this._polar(20, 20, 18, start);
            const [x2, y2] = this._polar(20, 20, 18, end);
            const largeArc = sweep > 180 ? 1 : 0;
            return {
                key: `${item.label}-${index}`,
                label: item.label,
                text: this._format(item.value, widget.value_format),
                pct: Math.round((Math.abs(item.value) / total) * 100),
                // A status rule may colour the slice; the palette is the fallback.
                color: item.color || PIE_PALETTE[index % PIE_PALETTE.length],
                status: item.status || "",
                message: item.message || "",
                path: `M20 20 L${x1} ${y1} A18 18 0 ${largeArc} 1 ${x2} ${y2} Z`,
            };
        });
    }

    _polar(centerX, centerY, radius, degrees) {
        const radians = (degrees * Math.PI) / 180;
        return [
            (centerX + radius * Math.cos(radians)).toFixed(2),
            (centerY + radius * Math.sin(radians)).toFixed(2),
        ];
    }

    _numberText(value, decimals) {
        return (Number(value) || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: decimals,
        });
    }

    _format(value, format) {
        if (value === null || value === undefined) {
            return "—";
        }
        const currency = this.state.meta.currency || {};
        const decimals = currency.decimal_places === undefined ? 2 : currency.decimal_places;
        if (format === "percent") {
            return `${this._numberText(value, 1)}%`;
        }
        if (format === "hours") {
            return `${this._numberText(value, 1)} h`;
        }
        if (format === "currency") {
            const text = this._numberText(value, decimals);
            const symbol = currency.symbol || "";
            if (!symbol) {
                return text;
            }
            return currency.position === "after" ? `${text} ${symbol}` : `${symbol} ${text}`;
        }
        return this._numberText(value, 2);
    }

    _notify(message) {
        this.notification.add(message, { type: "info" });
    }

    _notifyError(error) {
        // The server wraps a ValidationError in an envelope whose ``message`` is
        // "Odoo Server Error"; the real text lives in ``error.data.message``.
        const data = (error && error.data) || {};
        const message = data.message || (error && error.message) || _t("Something went wrong.");
        this.notification.add(message, { type: "danger" });
    }
}

registry.category("actions").add("od19_dashboard.builder", DashboardAction);
