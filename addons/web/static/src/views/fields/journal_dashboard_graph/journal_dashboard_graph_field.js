import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor, hexToRGBA, getCustomColor } from "@web/core/colors/colors";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";

const colorScheme = cookie.get("color_scheme");
const GRAPH_GRID_COLOR = getCustomColor(colorScheme, "#d8dadd", "#3C3E4B");
const GRAPH_LABEL_COLOR = getCustomColor(colorScheme, "#111827", "#E4E4E4");
export class JournalDashboardGraphField extends Component {
    static template = "web.JournalDashboardGraphField";
    static props = {
        ...standardFieldProps,
        graphType: String,
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");
        this.data = JSON.parse(this.props.record.data[this.props.name]);

        onWillStart(async () => await loadBundle("web.chartjs_lib"));

        useEffect(() => {
            this.renderChart();
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        });
    }

    /**
     * Instantiates a Chart (Chart.js lib) to render the graph according to
     * the current config.
     */
    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        let config;
        if (this.props.graphType === "line") {
            config = this.getLineChartConfig();
        } else if (this.props.graphType === "bar") {
            config = this.getBarChartConfig();
        }
        this.chart = new Chart(this.canvasRef.el, config);
    }
    getLineChartConfig() {
        const labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        const color10 = getColor(3, cookie.get("color_scheme"), "odoo");
        const borderColor = this.data[0].is_sample_data ? hexToRGBA(color10, 0.1) : color10;
        const backgroundColor = this.data[0].is_sample_data
            ? hexToRGBA(color10, 0.05)
            : hexToRGBA(color10, 0.2);
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        borderColor,
                        data: this.data[0].values,
                        fill: "start",
                        label: this.data[0].key,
                        borderWidth: 2,
                    },
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

    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColor = [];

        const color13 = getColor(2, cookie.get("color_scheme"), "odoo");
        const color19 = getColor(1, cookie.get("color_scheme"), "odoo");
        this.data[0].values.forEach((pt) => {
            data.push(pt.value);
            labels.push(pt.label);
            if (pt.type === "past") {
                backgroundColor.push(color13);
            } else if (pt.type === "future") {
                backgroundColor.push(color19);
            } else {
                backgroundColor.push(getCustomColor(colorScheme, "#ebebeb", "#3C3E4B"));
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
                },
            },
        };
    }
}

export const journalDashboardGraphField = {
    component: JournalDashboardGraphField,
    supportedTypes: ["text"],
    extractProps: ({ attrs }) => ({
        graphType: attrs.graph_type,
    }),
};

registry.category("fields").add("dashboard_graph", journalDashboardGraphField);
