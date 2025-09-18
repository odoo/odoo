// @ts-check

/** @module @web/fields/basic/float_factor/float_factor_field - Float field that applies a multiplication factor for display and storage */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FloatField, floatField } from "@web/fields/basic/float/float_field";

export class FloatFactorField extends FloatField {
    static props = {
        ...FloatField.props,
        factor: { type: Number, optional: true },
    };
    static defaultProps = {
        ...FloatField.defaultProps,
        factor: 1,
    };

    /**
     * @param {string} value - user input to parse
     * @returns {number} parsed float divided by the factor
     */
    parse(value) {
        return super.parse(value) / this.props.factor;
    }

    /** @returns {number} stored value multiplied by the factor */
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
