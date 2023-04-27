/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatInteger } from "../formatters";
import { parseInteger } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

import { Component } from "@odoo/owl";

export class IntegerField extends Component {
    static template = "web.IntegerField";
    static props = {
        ...standardFieldProps,
        inputType: { type: String, optional: true },
        step: { type: Number, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        inputType: "text",
    };

    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseInteger(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        if (!this.props.readonly && this.props.inputType === "number") {
            return this.props.record.data[this.props.name];
        }
        return formatInteger(this.props.record.data[this.props.name]);
    }
}

export const integerField = {
    component: IntegerField,
    displayName: _lt("Integer"),
    supportedOptions: [
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
    supportedTypes: ["integer"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps: ({ attrs, options }) => ({
        inputType: options.type,
        step: options.step,
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("integer", integerField);
