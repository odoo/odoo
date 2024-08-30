import { cookie } from "@web/core/browser/cookie";
import { getColor, hexToRGBA, getCustomColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

const colorScheme = cookie.get("color_scheme");
const GRAPH_GRID_COLOR = getCustomColor(colorScheme, "#d8dadd", "#3C3E4B");
const GRAPH_LABEL_COLOR = getCustomColor(colorScheme, "#111827", "#E4E4E4");

export class WorkcenterDashboardGraphField extends JournalDashboardGraphField{
    getLineChartConfig() {
        const labels = this.data[0].values[0].map(function (pt) {
            return pt.x;
        });
        const redColor = getColor(8, cookie.get("color_scheme"));
        const blueColor = getColor(2, cookie.get("color_scheme"));
        const loadLineColor = this.data[0].is_sample_data ? hexToRGBA(blueColor, 0.1) : blueColor;
        const roofLineColor = this.data[0].is_sample_data ? hexToRGBA(redColor, 0.1) : redColor;
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        borderColor: loadLineColor,
                        data: this.data[0].values[0],
                        fill: false,
                        label: this.data[0].key,
                        borderWidth: 2,
                    },
                    {
                        borderColor: roofLineColor,
                        data: this.data[0].values[1],
                        fill: false,
                        label: 'Max Load',
                        borderWidth: 2,
                    }
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: !this.data[0].is_sample_data,
                        intersect: false,
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
                            color: GRAPH_GRID_COLOR,
                            offset: true,
                        },
                        ticks: {
                            color: GRAPH_LABEL_COLOR,
                        },
                        border: {
                            color: GRAPH_GRID_COLOR,
                        },
                    },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                    point: {
                        radius: 0,
                    }
                },
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
