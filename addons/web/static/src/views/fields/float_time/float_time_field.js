/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatFloatTime } from "../formatters";
import { parseFloatTime } from "../parsers";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

const { Component } = owl;

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
    invalidate: { type: Function, optional: true },
};
FloatTimeField.defaultProps = {
    invalidate: () => {},
};

FloatTimeField.displayName = _lt("Time");
FloatTimeField.supportedTypes = ["float"];

FloatTimeField.isEmpty = () => false;
FloatTimeField.extractProps = (fieldName, record) => {
    return {
        invalidate: () => record.setInvalidField(fieldName),
    };
};

registry.category("fields").add("float_time", FloatTimeField);
