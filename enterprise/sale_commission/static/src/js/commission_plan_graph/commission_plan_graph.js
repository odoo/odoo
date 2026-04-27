import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { getColor } from "@web/core/colors/colors";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { cookie } from "@web/core/browser/cookie";

export class CommissionGraphField extends Component {
    static template = "sale_commission.GraphField";
    static props = {
        ...standardFieldProps,
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
        this.data = JSON.parse(this.props.record.data[this.props.name]);
        this.chart = new Chart(this.canvasRef.el, this.getLineChartConfig());
    }

    GCD(a, b) {
        if (a < b) return this.GCD(b, a);
        if (b == 0) return a;
        return this.GCD(b, a % b);
    }

    getLineChartConfig() {
        const labels = this.data.values.map(function (pt) {
            return pt.x;
        });

        let gcd = 0;
        this.data.values.forEach(v => {
            gcd = this.GCD(v.x, gcd);
        })

        const color10 = getColor(3, cookie.get("color_scheme"), "odoo");
        const currency = this.data.currency;
        return {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        color10,
                        data: this.data.values,
                        fill: "start",
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: true,
                        intersect: false,
                        position: "nearest",
                        caretSize: 0,
                    },
                },
                scales: {
                    x: {
                        type: 'linear',
                        ticks: {
                            stepSize: gcd,
                            callback: function(value, index, ticks) {
                                return value + '%'
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        ticks: {
                            callback: function(value, index, ticks) {
                                return value + currency
                            }
                        }
                    },
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

export const commissionGraphField = {
    component: CommissionGraphField,
    supportedTypes: ["text"],
};

registry.category("fields").add("commission_graph", commissionGraphField);
