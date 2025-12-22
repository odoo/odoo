import { registry } from "@web/core/registry";
import { floatField, FloatField } from "../float/float_field";
import { _t } from "@web/core/l10n/translation";

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
