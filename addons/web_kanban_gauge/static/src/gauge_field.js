/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";

export class GaugeField extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

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

    get formattedValue() {
        return formatFloat(this.props.value, { humanReadable: true, decimals: 1 });
    }

    renderChart() {
        const gaugeValue = this.props.value;
        let maxValue = Math.max(gaugeValue, this.props.record.data[this.props.maxValueField] || this.props.maxValue);
        let maxLabel = maxValue;
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
            maxLabel = 0;
        }
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        backgroundColor: ["#1f77b4", "#dddddd"],
                        label: this.props.title,
                    },
                ],
            },
            options: {
                circumference: Math.PI,
                rotation: -Math.PI,
                responsive: true,
                tooltips: {
                    displayColors: false,
                    callbacks: {
                        label: function (tooltipItems) {
                            if (tooltipItems.index === 0) {
                                return _t("Value: ") + gaugeValue;
                            }
                            return _t("Max: ") + maxLabel;
                        },
                    },
                },
                title: {
                    display: true,
                    text: this.props.title,
                    padding: 4,
                },
                layout: {
                    padding: {
                        bottom: 5,
                    },
                },
                maintainAspectRatio: false,
                cutoutPercentage: 70,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

GaugeField.template = "web.GaugeField";
GaugeField.props = {
    ...standardFieldProps,
    maxValueField: { type: String },
    title: { type: String },
    maxValue: { type: Number },
};

GaugeField.extractProps = ({ attrs, field }) => {
    return {
        maxValueField: attrs.options.max_field || "",
        title: attrs.options.title || field.string,
        maxValue: attrs.options.max_value || 100,
    };
};

registry.category("fields").add("gauge", GaugeField);
