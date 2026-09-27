import { registry } from "@web/core/registry";
import { getShortLabel } from "../labeled_field_short_labels";
import {
    MonetaryField,
    monetaryField,
    monetaryFieldProps
} from "@web/views/fields/monetary/monetary_field";
import { t, useProps } from "@odoo/owl";

export class LabeledMonetaryField extends MonetaryField {
    static template = "sale.LabeledMonetaryField";
    props = useProps({
        ...monetaryFieldProps,
        label: t.string(),
    });
}

export const labeledMonetaryField = {
    ...monetaryField,
    component: LabeledMonetaryField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = monetaryField.extractProps(fieldInfo, dynamicInfo);
        props.label = getShortLabel(fieldInfo.name) ?? fieldInfo.string;
        return props;
    },
};

registry.category("fields").add("labeled_monetary_field", labeledMonetaryField);
