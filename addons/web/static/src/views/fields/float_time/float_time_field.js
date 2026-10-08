import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { parseFloatTime } from "../parsers";

import { Component, signal, t, useProps } from "@odoo/owl";

export const floatTimeFieldProps = {
    ...standardFieldProps,
    showSeconds: t.boolean().optional(),
    numeric: t.boolean().optional(false),
    unit: t.selection(["hours", "minutes", "seconds"]).optional("hours"),
};

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    props = useProps(floatTimeFieldProps);
    numpadDecimalRef = signal.ref();

    setup() {
        this.inputFloatTimeRef = useInputField({
            getValue: () => this.formattedValue,
            ref: this.numpadDecimalRef,
            parse: (v) => this.parseValue(v),
            preview: (v) => formatFloatTime(v, this.formatOptions),
        });
        useNumpadDecimal(this.numpadDecimalRef);
    }

    get formatOptions() {
        return {
            showSeconds: this.props.showSeconds,
            numeric: this.props.numeric,
            unit: this.props.unit,
        };
    }

    parseValue(value) {
        return parseFloatTime(value, this.props.unit);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get formattedValue() {
        return formatFloatTime(this.value, this.formatOptions);
    }
}

export const floatTimeField = {
    component: FloatTimeField,
    displayName: _t("Time"),
    supportedOptions: [
        {
            label: _t("Show seconds"),
            name: "show_seconds",
            type: "boolean",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
            default: "text",
        },
        {
            label: _t("Numeric"),
            name: "numeric",
            type: "boolean",
        },
        {
            label: _t("Unit"),
            name: "unit",
            type: "selection",
            default: "hours",
            choices: [
                { label: _t("Hours"), value: "hours" },
                { label: _t("Minutes"), value: "minutes" },
                { label: _t("Seconds"), value: "seconds" },
            ],
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ options }) => ({
        showSeconds: Boolean(options.show_seconds),
        numeric: Boolean(options.numeric),
        unit: options.unit,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
