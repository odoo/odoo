/** @odoo-module **/

import { registry } from "@web/core/registry";
import { floatField, FloatField } from "../float/float_field";

export class FloatFactorField extends FloatField {
    static props = {
        ...FloatField.props,
        factor: { type: Number, optional: true },
    };
    static defaultProps = {
        ...FloatField.defaultProps,
        factor: 1,
    };

    parse(value) {
        let factorValue = value / this.props.factor;
        if (this.props.inputType !== "number") {
            factorValue = factorValue.toString();
        }
        return super.parse(factorValue);
    }

    get value() {
        return this.props.record.data[this.props.name] * this.props.factor;
    }
}

export const floatFactorField = {
    ...floatField,
    component: FloatFactorField,
    extractProps: (fieldInfo) => ({
        ...floatField.extractProps(fieldInfo),
        factor: fieldInfo.options.factor,
    }),
};

registry.category("fields").add("float_factor", floatFactorField);
