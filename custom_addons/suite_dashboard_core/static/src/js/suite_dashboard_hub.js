/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, onWillStart, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";

const LOCALE = "pt-BR";
const CHART_COLORS = ["#0f766e", "#2563eb", "#f59e0b", "#ef4444", "#7c3aed", "#0891b2"];

function formatNumber(value) {
    return Number(value || 0).toLocaleString(LOCALE, {
        maximumFractionDigits: 2,
    });
}

function formatCurrency(value, currency) {
    if (!currency?.name) {
        return formatNumber(value);
    }
    return new Intl.NumberFormat(LOCALE, {
        style: "currency",
        currency: currency.name,
    }).format(Number(value || 0));
}

function formatDate(value) {
    if (!value) {
        return "";
    }
    return new Intl.DateTimeFormat(LOCALE, {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(new Date(`${value}T12:00:00`));
}

function deltaClass(delta) {
    if (delta === null || delta === undefined) {
        return "";
    }
    return delta >= 0 ? "is-positive" : "is-negative";
}

function toneClass(tone) {
    return tone ? `is-${tone}` : "";
}

class SuiteDashboardChartWidget extends Component {
    static template = "suite_dashboard_core.SuiteDashboardChartWidget";
    static props = ["widget"];

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;

        onMounted(() => this.renderChart());
        useEffect(
            () => {
                this.renderChart();
                return () => this.destroyChart();
            },
            () => [JSON.stringify(this.props.widget.chart || {})]
        );
        onWillUnmount(() => this.destroyChart());
    }

    destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    renderChart() {
        const chartData = this.props.widget.chart;
        if (!this.canvasRef.el || !window.Chart || !chartData) {
            return;
        }

        this.destroyChart();
        const chartType = chartData.type === "donut" ? "doughnut" : chartData.type;
        const datasets = (chartData.datasets || []).map((dataset, index) => ({
            borderWidth: chartType === "bar" ? 0 : 2,
            tension: 0.35,
            fill: chartType === "line",
            backgroundColor:
                dataset.backgroundColor ||
                (chartType === "donut"
                    ? CHART_COLORS
                    : CHART_COLORS[index % CHART_COLORS.length]),
            borderColor: dataset.borderColor || CHART_COLORS[index % CHART_COLORS.length],
            ...dataset,
        }));

        this.chart = new window.Chart(this.canvasRef.el, {
            type: chartType,
            data: {
                labels: chartData.labels || [],
                datasets,
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 450,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: "bottom",
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8,
                            color: "#475569",
                        },
                    },
                    tooltip: {
                        intersect: false,
                    },
                },
                scales:
                    chartType === "donut"
                        ? {}
                        : {
                              x: {
                                  grid: { display: false },
                                  ticks: { color: "#64748b" },
                              },
                              y: {
                                  grid: { color: "rgba(148, 163, 184, 0.18)" },
                                  ticks: { color: "#64748b" },
                              },
                          },
            },
        });
    }
}

export class SuiteDashboardHub extends Component {
    static template = "suite_dashboard_core.SuiteDashboardHub";
    static components = { SuiteDashboardChartWidget };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            error: null,
            workspaceId: this.props?.action?.params?.workspace_id || null,
            payload: null,
            filters: {
                date_filter: "mtd",
                date_from: null,
                date_to: null,
                company_ids: [],
            },
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            if (this.state.workspaceId) {
                await this.loadWorkspacePayload(this.state.workspaceId, this.state.filters);
            } else {
                await this.loadDefaultPayload();
            }
        });
    }

    get payload() {
        return this.state.payload || {};
    }

    get workspaces() {
        return this.payload.available_workspaces || [];
    }

    get workspace() {
        return this.payload.workspace || null;
    }

    get widgets() {
        return this.payload.widgets || [];
    }

    get heroMetrics() {
        return this.payload.hero_metrics || [];
    }

    get quickAccess() {
        return this.payload.quick_access || [];
    }

    get aiSummary() {
        return this.payload.ai_context?.summary || "";
    }

    get aiHighlights() {
        return this.payload.ai_context?.highlights || [];
    }

    get companyOptions() {
        return this.payload.available_filters?.company_options || [];
    }

    async loadDefaultPayload(filterOverrides = {}) {
        const nextFilters = { ...this.state.filters, ...filterOverrides };
        this.state.loading = true;
        this.state.error = null;
        try {
            const payload = await this.orm.call(
                "suite.dashboard.workspace",
                "get_default_dashboard_payload",
                [nextFilters]
            );
            this.applyPayload(payload);
        } catch (error) {
            this.state.error = error.message;
        } finally {
            this.state.loading = false;
        }
    }

    async loadWorkspacePayload(workspaceId, filterOverrides = {}) {
        this.state.loading = true;
        this.state.error = null;
        try {
            const nextFilters = {
                ...(this.state.payload?.filters || this.state.filters),
                ...filterOverrides,
            };
            const payload = await this.orm.call(
                "suite.dashboard.workspace",
                "get_dashboard_payload",
                [[workspaceId], nextFilters]
            );
            this.applyPayload(payload);
        } catch (error) {
            this.state.error = error.message;
        } finally {
            this.state.loading = false;
        }
    }

    applyPayload(payload) {
        this.state.payload = payload;
        this.state.workspaceId = payload?.workspace?.id || null;
        this.state.filters = {
            date_filter: payload?.filters?.date_filter || "mtd",
            date_from: payload?.filters?.date_from || null,
            date_to: payload?.filters?.date_to || null,
            company_ids: payload?.filters?.company_ids || [],
        };
    }

    async onWorkspaceChange(ev) {
        const workspaceId = parseInt(ev.target.value, 10);
        const selected = this.workspaces.find((workspace) => workspace.id === workspaceId);
        const defaultFilter = selected?.default_date_filter || "mtd";
        const nextFilters = {
            date_filter: defaultFilter,
            date_from: null,
            date_to: null,
            company_ids: this.state.filters.company_ids || [],
        };
        await this.loadWorkspacePayload(workspaceId, nextFilters);
    }

    async onPeriodSelect(dateFilter) {
        const nextFilters = {
            ...this.state.filters,
            date_filter: dateFilter,
        };
        if (dateFilter !== "custom") {
            nextFilters.date_from = null;
            nextFilters.date_to = null;
        }
        await this.loadWorkspacePayload(this.state.workspaceId, nextFilters);
    }

    onCustomDateInput(fieldName, ev) {
        this.state.filters[fieldName] = ev.target.value;
    }

    async onApplyCustomDates() {
        await this.loadWorkspacePayload(this.state.workspaceId, {
            ...this.state.filters,
            date_filter: "custom",
        });
    }

    async onRefresh() {
        if (this.state.workspaceId) {
            await this.loadWorkspacePayload(this.state.workspaceId, this.state.filters);
        } else {
            await this.loadDefaultPayload(this.state.filters);
        }
    }

    async onToggleFavorite() {
        if (!this.state.workspaceId) {
            return;
        }
        try {
            await this.orm.call("suite.dashboard.workspace", "toggle_favorite", [[this.state.workspaceId]]);
            await this.onRefresh();
            this.notification.add("Favorito atualizado.", { type: "success" });
        } catch (error) {
            this.notification.add(error.message, { type: "danger" });
        }
    }

    async onCreateSnapshot() {
        if (!this.state.workspaceId) {
            return;
        }
        try {
            const action = await this.orm.call(
                "suite.dashboard.workspace",
                "action_create_snapshot",
                [[this.state.workspaceId], this.state.filters]
            );
            if (action) {
                this.action.doAction(action);
            }
        } catch (error) {
            this.notification.add(error.message, { type: "danger" });
        }
    }

    async onDuplicateWorkspace() {
        if (!this.state.workspaceId) {
            return;
        }
        try {
            const action = await this.orm.call(
                "suite.dashboard.workspace",
                "action_duplicate_workspace",
                [[this.state.workspaceId]]
            );
            if (action) {
                this.action.doAction(action);
            }
        } catch (error) {
            this.notification.add(error.message, { type: "warning" });
        }
    }

    openWorkspaceAdmin() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Workspaces",
            res_model: "suite.dashboard.workspace",
            view_mode: "list,form",
            target: "current",
        });
    }

    onQuickAccess(item) {
        if (item?.action) {
            this.action.doAction(item.action);
        }
    }

    onWidgetDrilldown(widget) {
        if (widget?.drilldown_action) {
            this.action.doAction(widget.drilldown_action);
        }
    }

    async onToggleCompany(companyId) {
        const selectedIds = new Set((this.state.filters.company_ids || []).map(Number));
        if (selectedIds.has(companyId)) {
            if (selectedIds.size === 1) {
                this.notification.add("Selecione ao menos uma empresa.", { type: "warning" });
                return;
            }
            selectedIds.delete(companyId);
        } else {
            selectedIds.add(companyId);
        }
        await this.loadWorkspacePayload(this.state.workspaceId, {
            ...this.state.filters,
            company_ids: [...selectedIds],
        });
    }

    isPeriodActive(key) {
        return this.state.filters.date_filter === key;
    }

    isCompanySelected(companyId) {
        return (this.state.filters.company_ids || []).includes(companyId);
    }

    formatValue(value, format = "number") {
        if (format === "currency") {
            return formatCurrency(value, this.payload.filters?.currency);
        }
        return formatNumber(value);
    }

    formatWidgetValue(widget) {
        if (widget.display_value) {
            return widget.display_value;
        }
        return this.formatValue(widget.value, widget.value_format);
    }

    formatMetricValue(metric) {
        if (metric.display_value) {
            return metric.display_value;
        }
        return this.formatValue(metric.value, "currency");
    }

    formatCellValue(column, row) {
        const value = row?.[column.key];
        if (column.type === "currency") {
            return this.formatValue(value, "currency");
        }
        if (column.type === "number") {
            return this.formatValue(value, "number");
        }
        return value;
    }

    formatGeneratedAt() {
        const generatedAt = this.payload.generated_at;
        if (!generatedAt) {
            return "";
        }
        return new Intl.DateTimeFormat(LOCALE, {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date(generatedAt));
    }

    formatDateRange() {
        const filters = this.payload.filters || {};
        if (filters.date_filter !== "custom") {
            return filters.date_range_label || "";
        }
        return `${formatDate(filters.date_from)} - ${formatDate(filters.date_to)}`;
    }

    cardStyle(widget) {
        const accent = widget.accent_color || "#2563eb";
        const colSpan = widget.layout?.col_span || 3;
        const rowSpan = widget.layout?.row_span || 1;
        return `--card-accent: ${accent}; grid-column: span ${colSpan}; grid-row: span ${rowSpan};`;
    }

    quickAccessStyle(item) {
        return `--card-accent: ${item.accent_color || "#2563eb"};`;
    }

    metricToneClass(metric) {
        return toneClass(metric.tone);
    }

    deltaClass(widget) {
        return deltaClass(widget.delta_pct);
    }
}

registry.category("actions").add("suite_dashboard_hub", SuiteDashboardHub);
