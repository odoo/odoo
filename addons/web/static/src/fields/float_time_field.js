/** @odoo-module **/

import { registry } from "@web/core/registry";
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
            value = this.props.parse(ev.target.value);
        } catch {
            isValid = false;
            this.props.setAsInvalid(this.props.name);
        }
        if (isValid) {
            this.props.update(value);
        }
    }

    get formattedValue() {
        return this.props.format(this.props.value);
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
        setAsInvalid: record.setInvalidField.bind(record),
    };
};

registry.category("fields").add("float_time", FloatTimeField);
