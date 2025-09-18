// @ts-check

/** @module @web/fields/basic/float_time/float_time_field - Time duration input that stores hours as a float (e.g. 1.5 = 1h30) */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/fields/formatters";
import { useInputField } from "@web/fields/input_field_hook";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";
import { parseFloatTime } from "@web/fields/parsers";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        displaySeconds: { type: Boolean, optional: true },
    };
    static defaultProps = {
        inputType: "text",
    };

    setup() {
        this.inputFloatTimeRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTime(v),
        });
        useNumpadDecimal();
    }

    /** @returns {string} float value formatted as HH:MM (or HH:MM:SS) */
    get formattedValue() {
        return formatFloatTime(this.props.record.data[this.props.name], {
            displaySeconds: this.props.displaySeconds,
        });
    }
}

export const floatTimeField = {
    component: FloatTimeField,
    displayName: _t("Time"),
    supportedOptions: [
        {
            label: _t("Display seconds"),
            name: "display_seconds",
            type: "boolean",
        },
        {
            label: _t("Type"),
            name: "type",
            type: "string",
            default: "text",
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ options }) => ({
        displaySeconds: options.displaySeconds,
        inputType: options.type,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
