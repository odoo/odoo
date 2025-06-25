import { cookie } from "@web/core/browser/cookie";
import { getColor, getCustomColor } from "@web/core/colors/colors";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { JournalDashboardGraphField } from "@web/views/fields/journal_dashboard_graph/journal_dashboard_graph_field";

export class PickingTypeDashboardGraphField extends JournalDashboardGraphField {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }
    getBarChartConfig() {
        // Only bar chart is available for picking types
        const data = [];
        const labels = [];
        const backgroundColor = [];

        const colorPast = getColor(8, cookie.get("color_scheme"));
        const colorPresent = getColor(16, cookie.get("color_scheme"));
        const colorFuture = getColor(12, cookie.get("color_scheme"));
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
                backgroundColor.push(getCustomColor(cookie.get("color_scheme"), "#ebebeb", "#3C3E4B"));
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
                onClick: (e) => {
                    const pickingTypeId = e.chart.config._config.options.pickingTypeId;
                    // If no picking type ID was provided, than this is sample data
                    if (!pickingTypeId) {
                        return;
                    }
                    const columnIndex = e.chart.tooltip.dataPoints[0].parsed.x;
                    const dateCategories = {
                        0: "before",
                        1: "yesterday",
                        2: "today",
                        3: "day_1",
                        4: "day_2",
                        5: "after",
                    };
                    const dateCategory = dateCategories[columnIndex];
                    const additionalContext = {
                        picking_type_id: pickingTypeId,
                        search_default_picking_type_id: [pickingTypeId],
                    };
                    // Add a filter for the given date category
                    additionalContext["search_default_".concat(dateCategory)] = true;
                    this.actionService.doAction("stock.click_dashboard_graph", {
                        additionalContext: additionalContext
                    });
                },
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
                pickingTypeId: this.data[0].picking_type_id,
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
