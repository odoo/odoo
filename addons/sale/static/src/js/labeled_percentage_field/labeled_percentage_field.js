import { registry } from "@web/core/registry";
import { PercentageField, percentageField } from "@web/views/fields/percentage/percentage_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { t, useProps } from "@odoo/owl";

export class LabeledPercentageField extends PercentageField {
    static template = "sale.LabeledPercentageField";
    props = useProps({
        ...standardFieldProps,
        digits: t.array().optional(),
        noSymbol: t.boolean().optional(),
        label: t.string(),
    });
}

export const labeledPercentageField = {
    ...percentageField,
    component: LabeledPercentageField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = percentageField.extractProps(fieldInfo, dynamicInfo);
        props.label = fieldInfo.string;
        return props;
    },
};

registry.category("fields").add("labeled_percentage_field", labeledPercentageField);
