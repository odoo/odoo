import { registry } from "@web/core/registry";
import { useProps, useEffect, t } from "@odoo/owl";
import {
    FloatField,
    floatField,
    floatFieldProps,
} from "@web/views/fields/float/float_field";

/**
 * Extension class to not display 0, as default, for strictily positive field, but rather 1.
 */

export const floatStrictlyPositiveProps = {
    ...floatFieldProps,
    placeholder: t.string().optional(),
};

export class FloatStrictlyPositiveField extends FloatField {
    props = useProps(floatStrictlyPositiveProps);

    setup() {
        super.setup();

        useEffect(() => {
            const el = typeof this.numpadDecimalRef === "function"
                ? this.numpadDecimalRef()
                : this.numpadDecimalRef?.el;
            if (el && this.props.placeholder) {
                el.placeholder = this.props.placeholder;
            }
        });
    }

    get formattedValue() {
        const val = this.value;

        if (val === false || val === undefined || val === null) {
            return "";
        }
        return super.formattedValue;
    }

    parse(value) {
        const trimmed = typeof value === "string" ? value.trim() : "";
        if (trimmed === "") {
            return 1;
        }
        return super.parse(value);
    }
}

export const floatStrictlyPositiveField = {
    ...floatField,
    component: FloatStrictlyPositiveField,
    extractProps: ({ attrs, options }) => ({
        ...floatField.extractProps({ attrs, options }),
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("float_strictly_positive", floatStrictlyPositiveField);
