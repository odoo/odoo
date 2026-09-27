import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FormattedDate extends Component {
    static template = "hr_skills.FormattedDate";

    props = useProps({
        ...standardFieldProps,
        dayFormat: t.string(),
        monthFormat: t.string(),
        yearFormat: t.string(),
        color: t.object(),
    });

    get value() {
        return this.props.record.data[this.props.name];
    }

    get placeholder() {
        return _t("Indefinite");
    }

    get colorClass() {
        const colors = Object.keys(this.props.color);
        if (colors) {
            for (const colorName of colors) {
                if (evaluateBooleanExpr(`${this.props.color[colorName]}`, this.props.record.evalContextWithVirtualIds)) {
                    return "text-" + colorName;
                }
            }
        }
        return ""
    }
}

export const formattedDate = {
    component: FormattedDate,
    supportedOptions: [
        {
            label: _t("Day Format"),
            name: "day_format",
            type: "string",
            default: "numeric",

        },
        {
            label: _t("Month Format"),
            name: "month_format",
            type: "string",
            default: "numeric",
        },
        {
            label: _t("Year Format"),
            name: "year_format",
            type: "string",
            default: "numeric",
        },
        {
            label: _t("Color"),
            name: "color",
            type: "string",
            default: {},
        },
    ],
    supportedTypes: ["date"],
    extractProps({ options }) {
        return {
            dayFormat: options.day_format || "numeric",
            monthFormat: options.month_format || "numeric",
            yearFormat: options.year_format || "numeric",
            color: options.color || {},
        };
    },
};

registry.category("fields").add("formatted_date", formattedDate);
