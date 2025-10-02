import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";

const fieldRegistry = registry.category("fields");

class OptionalFloatField extends FloatField {
    static template = "hr.OptionalFloatField";
    static props = {
        ...FloatField.props,
        placeholder: { type: String, optional: true },
    }

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
