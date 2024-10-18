import { _t } from "@web/core/l10n/translation";
import { cookie } from "@web/core/browser/cookie";
import { getColor, hexToRGBA, darkenColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class WorkcenterDashboardGraphField extends JournalDashboardGraphField{
    getBarChartConfig() {
        const labels = this.data[0].labels;
        const color19 = getColor(1, cookie.get("color_scheme"), "odoo");
        const color13 = getColor(2, cookie.get("color_scheme"), "odoo");
        const color10 = getColor(3, cookie.get("color_scheme"), "odoo");
        const loadBarColor = this.data[0].is_sample_data ? hexToRGBA(color19, 0.1) : color19;
        const excessBarColor = this.data[0].is_sample_data ? hexToRGBA(color13, 0.1) : color13;
        const maxLoadLineColor = this.data[0].is_sample_data ? hexToRGBA(color10, 0.1) : hexToRGBA(color10, 0.5);
        const darkColorOnHover = this.data[0].is_sample_data ? loadBarColor : darkenColor(loadBarColor, 0.1);
        return {
            type: 'scatter',
            data: {
                datasets: [
                    {
                        type: 'line',
                        borderColor: maxLoadLineColor,
                        // normally the line stops in the middle of the first and last columns, which is ugly
                        // to make it go through all the graph, the single point has been configured as a line
                        // in the middle of the graph and extended. The real line is not shown.
                        data: [,,this.data[0].values[1]],
                        showLine: false,
                        pointStyle: 'line',
                        pointRadius: 500,
                        pointBorderWidth: 2,
                        // this is so that hovering on the 'line' does not change its appearance
                        pointHoverRadius: 500,
                        pointHoverBorderWidth: 2,
                    },
                    {
                        type: 'bar',
                        backgroundColor: loadBarColor,
                        data: this.data[0].values[0],
                        label: "Total Load",
                        borderWidth: 0,
                        stack: 'mainStack',
                        hoverBackgroundColor: function(ctx, options) {
                            return (ctx.parsed._stacks.y[2] !== 0) ? excessBarColor :  darkColorOnHover;
                        },
                    },
                    {
                        type: 'bar',
                        backgroundColor: excessBarColor,
                        data: this.data[0].values[2],
                        label: "Excess Load",
                        borderWidth: 0,
                        stack: 'mainStack',
                    }
                ],
                labels,
            },
            options: {
                layout: {
                    autoPadding: false,
                },
                interaction: {
                    includeInvisible: true,
                    axis: 'x',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: !this.data[0].is_sample_data,
                        intersect: true,
                        mode: 'nearest',
                        position: 'nearest',
                        caretSize: 0,
                        filter: function(ctx) {
                            if (ctx.dataset.type !== 'line') {
                                return ctx;
                            }
                        },
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.datasetIndex === 1) {
                                    const totalLoadValue = Object.values(ctx.parsed._stacks.y._visualValues).reduce((accu, curr) => {return accu + curr}, 0);
                                    return _t(ctx.dataset.label + ": " + totalLoadValue + " hours");
                                }
                                return _t(ctx.dataset.label + ": " + ctx.parsed.y + " hours");
                            },
                            title: function(ctx) {
                                return "";
                            },
                        },
                    },
                },
                scales: {
                    y: {
                        display: false,
                        suggestedMax: this.data[0].values[1] * 1.5,
                        stacked: true,
                    },
                    x: {
                        type: 'category',
                        grid: {
                            display: false,
                        },
                        border: {
                            display: false,
                        },
                    },
                },
                maintainAspectRatio: false,
            },
        };
    }
}

export const workcenterDashboardGraphField = {
    component: WorkcenterDashboardGraphField,
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        graphType: attrs.graph_type,
    }),
};

registry.category("fields").add("workcenter_dashboard_graph", workcenterDashboardGraphField);
