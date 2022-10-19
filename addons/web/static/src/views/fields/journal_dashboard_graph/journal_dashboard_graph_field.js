/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor, hexToRGBA } from "@web/views/graph/colors";
import { standardFieldProps } from "../standard_field_props";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";

export class JournalDashboardGraphField extends Component {
    setup() {
        this.chart = null;
        this.cookies = useService("cookie");
        this.canvasRef = useRef("canvas");
        this.data = JSON.parse(this.props.value);

        onWillStart(() => loadJS("/web/static/lib/Chart/Chart.js"));

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
        // To perform its animations, ChartJS will perform each animation
        // step in the next animation frame. The initial rendering itself
        // is delayed for consistency. We can avoid this by manually
        // advancing the animation service.
        Chart.animationService.advance();
    }
    getLineChartConfig() {
        const labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        const color10 = getColor(10, this.cookies.current.color_scheme);
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

    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColor = [];

        const color13 = getColor(13, this.cookies.current.color_scheme);
        const color19 = getColor(19, this.cookies.current.color_scheme);
        this.data[0].values.forEach((pt) => {
            data.push(pt.value);
            labels.push(pt.label);
            if (pt.type === "past") {
                backgroundColor.push(color13);
            } else if (pt.type === "future") {
                backgroundColor.push(color19);
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
    graphType: String,
};

JournalDashboardGraphField.supportedTypes = ["text"];

JournalDashboardGraphField.extractProps = ({ attrs }) => {
    return {
        graphType: attrs.graph_type,
    };
};

registry.category("fields").add("dashboard_graph", JournalDashboardGraphField);
