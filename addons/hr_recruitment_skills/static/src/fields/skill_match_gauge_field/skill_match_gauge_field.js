import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";

export class SkillMatchGaugeField extends Component {
    static template = "hr_recruitment.SkillMatchGaugeField";
    static props = {
        ...standardFieldProps,
        maxValueField: { type: String, optional: true },
        maxValue: { type: Number, optional: true },
    };
    static defaultProps = {
        maxValue: 100,
    };

    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

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

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 0,
        });
    }

    renderChart() {
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = this.props.maxValueField
            ? this.props.record.data[this.props.maxValueField]
            : this.props.maxValue;
        const fgColor = gaugeValue > maxValue ? "#28a745" : "#714b67";
        maxValue = Math.max(gaugeValue, maxValue);
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
        }
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        backgroundColor: [fgColor, "#dddddd"],
                        label: this.title,
                    },
                ],
            },
            options: {
                circumference: 180,
                rotation: 270,
                responsive: true,
                maintainAspectRatio: false,
                cutout: "50%",
                plugins: {
                    title: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                aspectRatio: 2,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

export const skillMatchGaugeField = {
    component: SkillMatchGaugeField,
    supportedOptions: [
        {
            label: _t("Max value field"),
            name: "max_value_field",
            type: "field",
            availableTypes: ["integer", "float"],
        },
        {
            label: _t("Max value"),
            name: "max_value",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        maxValueField: options.max_field,
        maxValue: options.max_value,
    }),
};

registry.category("fields").add("skill_match_gauge_field", skillMatchGaugeField);
