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

FloatFactorField.template = "web.FloatFactorField";
FloatFactorField.components = { FloatField };
FloatFactorField.props = {
    ...standardFieldProps,
    inputType: { type: String, optional: true },
    digits: { type: Array, optional: true },
    invalidate: { type: Function, optional: true },
    factor: { type: Number, optional: true },
};
FloatFactorField.defaultProps = {
    inputType: "text",
    invalidate: () => {},
    factor: 1,
};

FloatFactorField.supportedTypes = ["float"];

FloatFactorField.isEmpty = () => false;
FloatFactorField.extractProps = (fieldName, record, attrs) => {
    return {
        invalidate: record.setInvalidField.bind(record),
        inputType: attrs.options.type,
        digits: attrs.digits ? JSON.parse(attrs.digits) : attrs.options.digits,
        factor: attrs.options.factor,
    };
};

registry.category("fields").add("float_factor", FloatFactorField);
