import { useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { IntegerField, integerField, integerFieldProps } from "@web/views/fields/integer/integer_field";


export class ExternalPlaceholderIntegerField extends IntegerField {
    static template = "stock.ExternalPlaceholderIntegerField";
    props = useProps({
        ...integerFieldProps,
        placeholder: t.string().optional(),
    });

    get formattedValue() {
        return this.value ? super.formattedValue : "";
    }

    get placeholderValue() {
        return this.props.placeholder || "...";
    }
}

registry.category("fields").add("external_placeholder_integer_field", {
    ...integerField,
    component: ExternalPlaceholderIntegerField,
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
});
