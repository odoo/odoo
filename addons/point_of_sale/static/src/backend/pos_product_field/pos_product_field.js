import {
    accountProductField,
    AccountProductField,
} from "@account/components/account_product_field/account_product_field";
import { registry } from "@web/core/registry";

export class PosProductField extends AccountProductField {
    static template = "point_of_sale.PosProductField";

    get label() {
        return (
            this.props.record.data["custom_attribute_value_ids"]?.records
                .map((r) => r.data.display_name)
                .join(", ") || ""
        );
    }
}

export const posProductField = {
    ...accountProductField,
    component: PosProductField,
};

registry.category("fields").add("pos_product_many2one", posProductField);
