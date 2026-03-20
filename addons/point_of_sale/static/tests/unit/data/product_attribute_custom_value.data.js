import { models } from "@web/../tests/web_test_helpers";

export class ProductAttributeCustomValue extends models.ServerModel {
    _name = "product.attribute.custom.value";

    _load_pos_data_fields() {
        return [
            "custom_value",
            "custom_product_template_attribute_value_id",
            "pos_order_line_id",
            "write_date",
        ];
    }
}
