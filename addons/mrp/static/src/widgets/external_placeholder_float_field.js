import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FloatField, floatField, floatFieldProps } from "@web/views/fields/float/float_field";
import { formatFloat } from "@web/views/fields/formatters";


export class ExternalPlaceholderFloatField extends FloatField {
    static template = "mrp.ExternalPlaceholderFloatField";
    props = props({
        ...floatFieldProps,
        placeholder: t.string().optional(),
    });

    get formattedValue() {
        return this.value ? super.formattedValue : "";
    }

    get placeholderValue() {
        const placeholder = this.props.record.data[this.props.placeholder];
        return placeholder !== undefined ? formatFloat(placeholder) : "...";
    }
}

registry.category("fields").add("external_placeholder_float_field", {
    ...floatField,
    component: ExternalPlaceholderFloatField,
    extractProps: ({ attrs }) => ({
        placeholder: attrs.placeholder,
    }),
});
