/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor, hexToRGBA } from "@web/views/graph/colors";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, useEffect, useRef } = owl;

export class WooDashboardGraphField extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");
        this.data = JSON.parse(this.props.value);
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this._rpc = useService("rpc");
        this.orm = useService("orm");

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

        Chart.animationService.advance();
    }

    getLineChartConfig() {
        const labels = this.data.values.map(function (pt) {
            return pt.x;
        });

        const borderColor = this.data.is_sample_data ? hexToRGBA(getColor(10), 0.1) : getColor(10);
        const backgroundColor = this.data.is_sample_data ? hexToRGBA(getColor(10), 0.05) : hexToRGBA(getColor(10), 0.2);

        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor,
                        borderColor,
                        data: this.data.values,
                        fill: "start",
                        label: this.data.key,
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

        if (this.data && this.data.values) {
            this.data.values.forEach(function (pt) {
                data.push(pt.y);
                labels.push(pt.x);

                const color =
                    pt.type === "past" ? getColor(13) : pt.type === "future" ? getColor(19) : "#ebebeb";
                backgroundColor.push(color);
            });
        }

        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        backgroundColor:'#2ecc71',
                        data,
                        fill: "start",
                        label: this.data.key,
                        borderWidth: 2,
                        pointStyle: 'bar',
                    },
                ],
            },
            options: {
                legend: {display: false},
                scales: {
                    xAxes: [{
                        position: 'bottom'
                    }],
                    yAxes: [{
                        position: 'left',
                        ticks: {
                            beginAtZero: true
                        },
                    }]
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.5,
                    }
                },
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
            },
        };
    }

    async _sortOrders(e) {
        const [record] = await this.orm.read(this.props.record.resModel, [this.props.record.resId], ["dashboard_graph_data"], { context: {'sort':  e.currentTarget.value} });
        this.data = JSON.parse(record.dashboard_graph_data);
        this.renderChart();
    }

    _SyncedProducts() {
        return this.actionService.doAction(this.data.product_data.product_action, {})
    }

    _SyncedCustomers() {
        return this.actionService.doAction(this.data.customer_data.customer_action, {})
    }

    _SyncedOrders() {
        return this.actionService.doAction(this.data.order_data.order_action, {})
    }

    _SyncedTaxes() {
        return this.actionService.doAction(this.data.tax_data.tax_action, {})
    }

    _SyncedAttributes() {
         return this.actionService.doAction(this.data.attribute_data.attribute_action, {})
    }

    _SyncedCategories() {
        return this.actionService.doAction(this.data.category_data.category_action, {})
    }

}

WooDashboardGraphField.template = "pragtech_woo_commerce.woo_graph_dashboard_widget";
WooDashboardGraphField.props = {
    ...standardFieldProps,
    graphType: String,
};

WooDashboardGraphField.supportedTypes = ["text"];

WooDashboardGraphField.extractProps = ({ attrs }) => {
    return {
        graphType: attrs.graph_type,
    };
};

registry.category("fields").add("woo_dashboard_graph", WooDashboardGraphField);