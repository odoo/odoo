import { cookie } from "@web/core/browser/cookie";
import { getColor } from "@web/core/colors/colors";
import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class PickingTypeDashboardGraphField extends JournalDashboardGraphField {
    getBarChartConfig() {
        // Only bar chart is available for picking types
        const data = [];
        const labels = [];
        const backgroundColor = [];

        const colorPast = getColor(13, cookie.get("color_scheme"));
        const colorPresent = getColor(19, cookie.get("color_scheme"));
        const colorFuture = getColor(5, cookie.get("color_scheme"));
        this.data[0].values.forEach((pt) => {
            data.push(pt.value);
            labels.push(pt.label);
            if (pt.type === "past") {
                backgroundColor.push(colorPast);
            } else if (pt.type === "present") {
                backgroundColor.push(colorPresent);
            } else if (pt.type === "future") {
                backgroundColor.push(colorFuture);
            } else {
                backgroundColor.push("#ebebeb");
            }
        });
        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        data,
                        fill: "start",
                        label: this.data[0].key,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
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
                        display: false,
                    },
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    }
}

export const pickingTypeDashboardGraphField = {
    component: PickingTypeDashboardGraphField,
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        graphType: attrs.graph_type,
    }),
};

registry.category("fields").add("picking_type_dashboard_graph", pickingTypeDashboardGraphField);
