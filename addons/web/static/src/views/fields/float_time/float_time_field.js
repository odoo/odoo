/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { parseFloatTime } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

import { Component } from "@odoo/owl";

export class FloatTimeField extends Component {
    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (v) => parseFloatTime(v),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        return formatFloatTime(this.props.value);
    }
}

FloatTimeField.template = "web.FloatTimeField";
FloatTimeField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    placeholder: { type: String, optional: true },
};
FloatTimeField.defaultProps = {
    inputType: "text",
};

FloatTimeField.displayName = _lt("Time");
FloatTimeField.supportedTypes = ["float"];

FloatTimeField.isEmpty = () => false;
FloatTimeField.extractProps = ({ attrs }) => {
    return {
        inputType: attrs.options.type,
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("float_time", FloatTimeField);
