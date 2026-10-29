import { cookie } from "@web/core/browser/cookie";
import { getColor, getCustomColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import {
    JournalDashboardGraphField,
    journalDashboardGraphField,
} from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

const colorScheme = cookie.get("color_scheme");
const GRAPH_GRID_COLOR = getCustomColor(colorScheme, "#d8dadd", "#3A3B41");
const GRAPH_LABEL_COLOR = getCustomColor(colorScheme, "#6c757d", "#ADB5BD");
const BAR_PERCENTAGE = 0.72;

// Bars and labels get an inner margin (layout padding), but the x axis line must keep the full width:
// Chart.js limits it to the chart area, so it is drawn by this plugin instead.
const fullWidthAxisPlugin = {
    id: "fullWidthAxis",
    afterDatasetsDraw(chart) {
        const { ctx, width, scales: { x } } = chart;
        const { color, width: lineWidth } = x.options.border;
        const y = Math.floor(x.top) + lineWidth / 2;
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
        ctx.restore();
    },
};

export class AccountJournalDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        if (this.data[0].type !== "monthly_total") {
            return super.getBarChartConfig();
        }

        return this.getMonthlyTotalChartConfig();
    }

    getMonthlyTotalChartConfig() {
        const totalColor = getColor(2, colorScheme, "odoo");

        return {
            type: "bar",
            data: {
                labels: this.data[0].labels,
                datasets: [
                    {
                        backgroundColor: totalColor,
                        data: this.data[0].values,
                        label: this.data[0].key,
                        borderWidth: 0,
                        categoryPercentage: 1,
                        barPercentage: BAR_PERCENTAGE,
                    },
                ],
            },
            options: {
                layout: {
                    padding: ({ chart }) => {
                        const halfGap = (1 - BAR_PERCENTAGE) / 2;
                        const padding = (halfGap * chart.width) / (chart.data.labels.length + 2 * halfGap);
                        return { left: padding, right: padding };
                    },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    y: {
                        display: false,
                    },
                    x: {
                        grid: {
                            display: false,
                        },
                        ticks: {
                            color: GRAPH_LABEL_COLOR,
                        },
                        border: {
                            color: GRAPH_GRID_COLOR,
                            width: 1,
                            display: false,  // drawn full width by fullWidthAxisPlugin
                        },
                    },
                },
                maintainAspectRatio: false,
                interaction: {
                    intersect: true,
                    mode: "nearest",
                },
            },
            plugins: [fullWidthAxisPlugin],
        };
    }
}

export const accountJournalDashboardGraphField = {
    ...journalDashboardGraphField,
    component: AccountJournalDashboardGraphField,
};

registry.category("fields").add("account_journal_dashboard_graph", accountJournalDashboardGraphField);
