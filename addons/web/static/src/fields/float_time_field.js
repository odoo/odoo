/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formatFloatTime } from "./formatters";
import { parseFloatTime } from "./parsers";
import { useInputField } from "./input_field_hook";
import { standardFieldProps } from "./standard_field_props";
import { useNumpadDecimal } from "./numpad_decimal_hook";

const { Component } = owl;
export class FloatTimeField extends Component {
    setup() {
        useInputField({ getValue: () => this.formattedValue, refName: "numpadDecimal" });
        useNumpadDecimal();
    }

    onChange(ev) {
        let isValid = true;
        let value;
        try {
            value = parseFloatTime(ev.target.value);
        } catch {
            isValid = false;
            this.props.setAsInvalid();
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get formattedValue() {
        return formatFloatTime(this.props.value);
    }
}

FloatTimeField.template = "web.FloatTimeField";
FloatTimeField.props = {
    ...standardFieldProps,
    setAsInvalid: { type: Function, optional: true },
};
FloatTimeField.defaultProps = {
    setAsInvalid: () => {},
};
FloatTimeField.isEmpty = () => false;
FloatTimeField.extractProps = (fieldName, record) => {
    return {
        setAsInvalid: () => record.setInvalidField(fieldName),
    };
};

registry.category("fields").add("float_time", FloatTimeField);
