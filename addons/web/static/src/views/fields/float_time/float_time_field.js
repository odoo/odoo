import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { parseFloatTime } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

import { Component } from "@odoo/owl";

export class FloatTimeField extends Component {
    static template = "web.FloatTimeField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        placeholder: { type: String, optional: true },
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
    extractProps: ({ attrs, options }) => ({
        displaySeconds: options.displaySeconds,
        inputType: options.type,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("float_time", floatTimeField);
