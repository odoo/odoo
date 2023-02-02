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
        return formatFloatTime(this.props.value, {roundToMin: this.props.roundToMin});
    }
}

FloatTimeField.template = "web.FloatTimeField";
FloatTimeField.props = {
    ...standardFieldProps,
    placeholder: { type: String, optional: true },
    roundToMin: { type: String, optional: true },
};

FloatTimeField.displayName = _lt("Time");
FloatTimeField.supportedTypes = ["float"];

FloatTimeField.isEmpty = () => false;
FloatTimeField.extractProps = ({ attrs }) => {
    return {
        placeholder: attrs.placeholder,
        roundToMin: attrs.roundToMin,
    };
};

registry.category("fields").add("float_time", FloatTimeField);
