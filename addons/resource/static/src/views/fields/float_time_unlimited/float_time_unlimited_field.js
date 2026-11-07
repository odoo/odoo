import { registry } from "@web/core/registry";
import { useProps, useEffect, t } from "@odoo/owl";
import { FloatTimeField, floatTimeField, floatTimeFieldProps} from "@web/views/fields/float_time/float_time_field";

/**
 * Extension class to support "Not Limited" type value, which considers an empty or zero value or negative value
 * as matching any positive value. This widget should only be used when the domain correspond to the positive.
 */

export const floatTimeUnlimitedFieldProps = {
    ...floatTimeFieldProps,
    placeholder: t.string().optional(),
};

export class FloatTimeUnlimitedField extends FloatTimeField {
    props = useProps(floatTimeUnlimitedFieldProps);

    setup() {
        super.setup();

        useEffect(() => {
            const el = this.inputFloatTimeRef?.() ||
                (typeof this.numpadDecimalRef === "function" ? this.numpadDecimalRef() : this.numpadDecimalRef?.el);
            if (el && this.props.placeholder) {
                el.placeholder = this.props.placeholder;
            }
        });
    }

    openPopover() {}

    onValueChange() {
        this.closePopover();
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

    parseValue(value) {
        const trimmed = typeof value === "string" ? value.trim() : "";
        if (trimmed === "" || trimmed.toLowerCase() === "not limited") {
            return 0.0;
        }
        return super.parseValue(value);
    }
}

export const floatTimeUnlimitedField = {
    ...floatTimeField,
    component: FloatTimeUnlimitedField,
    extractProps: ({ attrs, options }) => ({
        ...floatTimeField.extractProps({ attrs, options }),
        placeholder: attrs.placeholder,
    }),
};

registry.category("fields").add("float_time_unlimited", floatTimeUnlimitedField);
