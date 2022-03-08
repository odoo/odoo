/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { useAssets } from "@web/core/assets";

const { Component, useEffect, useRef } = owl;

export class JournalDashboardGraphField extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");
        this.data = JSON.parse(this.props.value);

        useAssets({ jsLibs: ["/web/static/lib/Chart/Chart.js"] });

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
            config = this._getLineChartConfig();
        } else if (this.props.graphType === "bar") {
            config = this._getBarChartConfig();
        }
        this.chart = new Chart(this.canvasRef.el, config);
        // To perform its animations, ChartJS will perform each animation
        // step in the next animation frame. The initial rendering itself
        // is delayed for consistency. We can avoid this by manually
        // advancing the animation service.
        Chart.animationService.advance();
    }
    _getLineChartConfig() {
        let labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        let borderColor = this.data[0].is_sample_data ? "#dddddd" : "#875a7b";
        let backgroundColor = this.data[0].is_sample_data ? "#ebebeb" : "#dcd0d9";
        return {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        data: this.data[0].values,
                        fill: "start",
                        label: this.data[0].key,
                        backgroundColor: backgroundColor,
                        borderColor: borderColor,
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{ display: false }],
                    xAxes: [{ display: false }],
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
                tooltips: {
                    intersect: false,
                    position: "nearest",
                    caretSize: 0,
                },
            },
        };
    }

    _getBarChartConfig() {
        let data = [];
        let labels = [];
        let backgroundColor = [];

        this.data[0].values.forEach(function (pt) {
            data.push(pt.value);
            labels.push(pt.label);
            let color =
                pt.type === "past" ? "#ccbdc8" : pt.type === "future" ? "#a5d8d7" : "#ebebeb";
            backgroundColor.push(color);
        });
        return {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        data: data,
                        fill: "start",
                        label: this.data[0].key,
                        backgroundColor: backgroundColor,
                    },
                ],
            },
            options: {
                legend: { display: false },
                scales: {
                    yAxes: [{ display: false }],
                },
                maintainAspectRatio: false,
                tooltips: {
                    intersect: false,
                    position: "nearest",
                    caretSize: 0,
                },
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
            },
        };
    }
}

JournalDashboardGraphField.template = "web.JournalDashboardGraphField";
JournalDashboardGraphField.props = {
    ...standardFieldProps,
    className: { type: String, optional: true },
    graphType: String,
};
JournalDashboardGraphField.extractProps = (fieldName, record) => {
    return {
        className: record.data["graph_type"] ? `o_graph_${record.data["graph_type"]}chart` : "",
        graphType: record.data["graph_type"],
    };
};

registry.category("fields").add("dashboard_graph", JournalDashboardGraphField);
