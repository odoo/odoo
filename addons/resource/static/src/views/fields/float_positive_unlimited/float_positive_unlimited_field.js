import { registry } from "@web/core/registry";
import { useProps, useEffect, t } from "@odoo/owl";
import {
    FloatField,
    floatField,
    floatFieldProps,
} from "@web/views/fields/float/float_field";

/**
 * Extension class to support "Not Limited" type value, which considers an empty or zero value or negative value
 * as matching any positive value. This widget should only be used when the domain correspond to the positive.
 */

export const floatUnlimitedFieldProps = {
    ...floatFieldProps,
    placeholder: t.string().optional(),
};

export class FloatUnlimitedField extends FloatField {
    props = useProps(floatUnlimitedFieldProps);

    setup() {
        super.setup();

        useEffect(
            () => {
                const el = typeof this.numpadDecimalRef === "function"
                    ? this.numpadDecimalRef()
                    : this.numpadDecimalRef?.el;
                if (el && this.props.placeholder) {
                    el.placeholder = this.props.placeholder;
                }
            },
            () => [this.props.placeholder, typeof this.numpadDecimalRef === "function" ? this.numpadDecimalRef() : null]
        );
    }

    get formattedValue() {
        const val = this.value;

        if (val <= 0 || val === false || val === undefined || val === null) {
            if (this.props.readonly) {
                return this.props.placeholder || "Not Limited";
            }
            return "";
        }
        return super.formattedValue;
    }

    parse(value) {
        const trimmed = typeof value === "string" ? value.trim() : "";
        if (trimmed === "" || trimmed.toLowerCase() === "not limited") {
            return 0.0;
        }
        return super.parse(value);
    }
}

export const floatUnlimitedField = {
    ...floatField,
    component: FloatUnlimitedField,
    extractProps: ({ attrs, options }) => ({
        ...floatField.extractProps({ attrs, options }),
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("float_positive_unlimited", floatUnlimitedField);
