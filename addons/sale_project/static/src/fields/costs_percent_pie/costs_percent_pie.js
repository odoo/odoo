import { t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { formatMonetary } from "@web/views/fields/formatters";
import {
    PercentPieField,
    percentPieField,
    percentPieFieldProps,
} from "@web/views/fields/percent_pie/percent_pie_field";

export class CostsPercentPieField extends PercentPieField {
    static template = "sale_project.CostsPercentPieField";

    props = useProps({
        ...percentPieFieldProps,
        cost_field_name: t.string().optional(),
    });

    get formattedCost() {
        const value = this.props.record.data[this.props.cost_field_name] || 0;
        return formatMonetary(value, { data: this.props.record.data, currency_field: "currency_id" });
    }
}

export const costsPercentPieField = {
    ...percentPieField,
    component: CostsPercentPieField,
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = percentPieField.extractProps(fieldInfo, dynamicInfo);
        props.cost_field_name = fieldInfo.attrs.cost_field_name;
        return props;
    },
};

registry.category("fields").add("costs_percentpie", costsPercentPieField);
