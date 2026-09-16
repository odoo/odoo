import {
    accountProductField,
    AccountProductField,
} from "@account/components/account_product_field/account_product_field";
import { registry } from "@web/core/registry";

export class PosOrderLineProductField extends AccountProductField {
    static template = "point_of_sale.SaleProductField";

    get label() {
        return (
            this.props.record.data["custom_attribute_value_ids"]?.records
                .map((r) => r.data.display_name)
                .join(", ") || ""
        );
    }
}

export const posOrderLineProductField = {
    ...accountProductField,
    component: PosOrderLineProductField,
};

registry.category("fields").add("pos_product_many2one", posOrderLineProductField);
