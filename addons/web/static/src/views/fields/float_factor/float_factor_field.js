/** @odoo-module **/

import { registry } from "@web/core/registry";
import { FloatField } from "../float/float_field";

import { Component } from "@odoo/owl";
export class FloatFactorField extends Component {
    get factor() {
        return this.props.factor;
    }

    get floatFieldProps() {
        const result = {
            ...this.props,
            value: this.props.value * this.factor,
            update: (value) => this.props.update(value / this.factor),
        };
        delete result.factor;
        return result;
    }
}

FloatFactorField.template = "web.FloatFactorField";
FloatFactorField.components = { FloatField };
FloatFactorField.props = {
    ...FloatField.props,
    factor: { type: Number, optional: true },
};
FloatFactorField.defaultProps = {
    ...FloatField.defaultProps,
    factor: 1,
};

FloatFactorField.supportedTypes = ["float"];

FloatFactorField.isEmpty = () => false;
FloatFactorField.extractProps = ({ attrs, field }) => {
    return {
        ...FloatField.extractProps({ attrs, field }),
        factor: attrs.options.factor,
    };
};

registry.category("fields").add("float_factor", FloatFactorField);
