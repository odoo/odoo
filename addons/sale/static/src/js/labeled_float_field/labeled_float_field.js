import { registry } from "@web/core/registry";
import { FloatField, floatField, floatFieldProps } from "@web/views/fields/float/float_field";
import { t, useProps } from "@odoo/owl";

export class LabeledFloatField extends FloatField {
    static template = "sale.LabeledFloatField";
    props = useProps({
        ...floatFieldProps,
        label: t.string(),
    });
}

export const labeledFloatField = {
    ...floatField,
    component: LabeledFloatField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = floatField.extractProps(fieldInfo, dynamicInfo);
        props.label = fieldInfo.string;
        return props;
    },
};

registry.category("fields").add("labeled_float_field", labeledFloatField);
