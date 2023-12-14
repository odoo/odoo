/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "../input_field_hook";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { formatFloat } from "../formatters";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class FloatField extends Component {
    static template = "web.FloatField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        step: { type: Number, optional: true },
        digits: { type: Array, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        inputType: "text",
    };

    setup() {
        this.inputRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => this.parse(v),
        });
        useNumpadDecimal();
    }

    parse(value) {
        return this.props.inputType === "number" ? Number(value) : parseFloat(value);
    }

    get digits() {
        const fieldDigits = this.props.record.fields[this.props.name].digits;
        return !this.props.digits && Array.isArray(fieldDigits) ? fieldDigits : this.props.digits;
    }
    get formattedValue() {
        if (this.props.inputType === "number" && !this.props.readonly && this.value) {
            return this.value;
        }
        return formatFloat(this.value, { digits: this.digits });
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}

export const floatField = {
    component: FloatField,
    displayName: _lt("Float"),
    supportedOptions: [
        {
            label: _lt("Digits"),
            name: "digits",
            type: "digits",
        },
        {
            label: _lt("Type"),
            name: "type",
            type: "string",
        },
        {
            label: _lt("Step"),
            name: "step",
            type: "number",
        },
    ],
    supportedTypes: ["float"],
    isEmpty: () => false,
    extractProps: ({ attrs, options }) => {
        // Sadly, digits param was available as an option and an attr.
        // The option version could be removed with some xml refactoring.
        let digits;
        if (attrs.digits) {
            digits = JSON.parse(attrs.digits);
        } else if (options.digits) {
            digits = options.digits;
        }

        return {
            inputType: options.type,
            step: options.step,
            digits,
            placeholder: attrs.placeholder,
        };
    },
};

registry.category("fields").add("float", floatField);
