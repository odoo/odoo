/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "./float_field";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
export class FloatFactorField extends Component {
    get floatFieldProps() {
        const result = {
            ...this.props,
            value: this.props.value * this.props.factor,
            update: (value) => this.props.update(value / this.props.factor),
        };
        delete result.factor;
        return result;
    }
}

FloatFactorField.components = { FloatField };
FloatFactorField.template = "web.FloatFactorField";
FloatFactorField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
    setAsInvalid: { type: Function, optional: true },
    field: { type: Object, optional: true },
    factor: { type: Number, optional: true },
};
FloatFactorField.defaultProps = {
    inputType: "text",
    setAsInvalid: () => {},
    factor: 1,
};
FloatFactorField.isEmpty = () => false;
FloatFactorField.extractProps = (fieldName, record, attrs) => {
    return {
        setAsInvalid: record.setInvalidField.bind(record),
        field: record.fields[fieldName], // To remove
        inputType: attrs.options.type,
        digits: attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits,
        factor: attrs.options.factor,
    };
};
FloatFactorField.supportedTypes = ["float"];

registry.category("fields").add("float_factor", FloatFactorField);
