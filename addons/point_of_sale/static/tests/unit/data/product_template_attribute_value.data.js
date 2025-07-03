import { models } from "@web/../tests/web_test_helpers";

export class ProductTemplateAttributeValue extends models.ServerModel {
    _name = "product.template.attribute.value";

    _load_pos_data_fields() {
        return [
            "attribute_id",
            "attribute_line_id",
            "product_attribute_value_id",
            "price_extra",
            "name",
            "is_custom",
            "html_color",
            "image",
            "exclude_for",
        ];
    }
}
