import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { floatField, FloatField, floatFieldProps } from "../float/float_field";
import { _t } from "@web/core/l10n/translation";

export class FloatFactorField extends FloatField {
    props = props({
        ...floatFieldProps,
        factor: t.number().optional(1),
    });

    parse(value) {
        return super.parse(value) / this.props.factor;
    }

    get value() {
        return this.props.record.data[this.props.name] * this.props.factor;
    }
}

export const floatFactorField = {
    ...floatField,
    component: FloatFactorField,
    supportedOptions: [
        ...floatField.supportedOptions,
        {
            label: _t("Factor"),
            name: "factor",
            type: "number",
        },
    ],
    extractProps({ options }) {
        const props = floatField.extractProps(...arguments);
        props.factor = options.factor;
        return props;
    },
};

registry.category("fields").add("float_factor", floatFactorField);
