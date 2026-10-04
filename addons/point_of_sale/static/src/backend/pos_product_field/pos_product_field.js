import {
    accountProductField,
    AccountProductField,
} from "@account/components/account_product_field/account_product_field";
import { registry } from "@web/core/registry";

export class PosProductField extends AccountProductField {
    static template = "point_of_sale.PosProductField";

    get label() {
        const { attribute_value_ids, custom_attribute_value_ids } = this.props.record.data;
        const customAttributeValues = custom_attribute_value_ids.records.map(
            ({ data }) => data.display_name
        );

        return attribute_value_ids.records
            .map(
                ({ data }) =>
                    customAttributeValues.find((value) => value.includes(data.display_name)) ||
                    data.display_name
            )
            .join(", ");
    }
}

export const posProductField = {
    ...accountProductField,
    component: PosProductField,
};

registry.category("fields").add("pos_product_field", posProductField);
