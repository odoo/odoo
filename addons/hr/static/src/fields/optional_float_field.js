import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { floatField, FloatField, floatFieldProps } from "@web/views/fields/float/float_field";

const fieldRegistry = registry.category("fields");

class OptionalFloatField extends FloatField {
    static template = "hr.OptionalFloatField";
    props = props({
        ...floatFieldProps,
        placeholder: t.string().optional(),
    });

    get formattedValue() {
        if (!this.value) {
            return "";
        }
        return super.formattedValue;
    }
}

const optionalFloatField = {
    ...floatField,
    component: OptionalFloatField,
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
};

fieldRegistry.add("optional_float_field", optionalFloatField);
