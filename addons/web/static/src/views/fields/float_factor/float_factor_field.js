/** @odoo-module **/

import { registry } from "@web/core/registry";
import { floatField, FloatField } from "../float/float_field";
import { Component } from "@odoo/owl";

export class FloatFactorField extends Component {
    static template = "web.FloatFactorField";
    static components = { FloatField };
    static props = {
        ...FloatField.props,
        factor: { type: Number, optional: true },
    };
    static defaultProps = {
        ...FloatField.defaultProps,
        factor: 1,
    };

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

export const floatFactorField = {
    ...floatField,
    component: FloatFactorField,
    extractProps: (params) => ({
        ...floatField.extractProps(params),
        factor: params.attrs.options.factor,
    }),
};

registry.category("fields").add("float_factor", floatFactorField);
