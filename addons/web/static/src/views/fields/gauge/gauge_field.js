import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useChart } from "@web/core/utils/chart_hook";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, t, useProps } from "@odoo/owl";

export class GaugeField extends Component {
    static template = "web.GaugeField";
    props = useProps({
        ...standardFieldProps,
        maxValueField: t.string().optional(),
        maxValue: t.number().optional(100),
        maxTooltip: t.string().optional(),
        title: t.string().optional(),
    });

    chart = useChart(() => this.getChartConfig());

    get title() {
        return this.props.title || this.props.record.fields[this.props.name].string || "";
    }

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 1,
        });
    }

    getChartConfig() {
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = this.props.maxValueField
            ? this.props.record.data[this.props.maxValueField]
            : this.props.maxValue;
        maxValue = Math.max(gaugeValue, maxValue);
        let maxLabel = this.props.maxTooltip ?? maxValue;
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
            maxLabel = 0;
        }
        return {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        backgroundColor: ["#1f77b4", "#dddddd"],
                        label: this.title,
                    },
                ],
            },
            options: {
                circumference: 180,
                rotation: 270,
                responsive: true,
                maintainAspectRatio: false,
                cutout: "70%",
                layout: {
                    padding: 5,
                },
                plugins: {
                    title: {
                        display: true,
                        text: this.title,
                        padding: 4,
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            label: function (tooltipItem) {
                                if (tooltipItem.dataIndex === 0) {
                                    return _t("Value: %(value)s", { value: gaugeValue });
                                }
                                return _t("Max: %(max)s", { max: maxLabel });
                            },
                        },
                    },
                },
                aspectRatio: 2,
            },
        };
    }
}

export const gaugeField = {
    component: GaugeField,
    supportedOptions: [
        {
            label: _t("Title"),
            name: "title",
            type: "string",
        },
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
        {
            label: _t("Max tooltip"),
            name: "max_tooltip",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        maxTooltip: options.max_tooltip,
        maxValueField: options.max_field,
        maxValue: options.max_value,
        title: options.title,
    }),
};

registry.category("fields").add("gauge", gaugeField);
