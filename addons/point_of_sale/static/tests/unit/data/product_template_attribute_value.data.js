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
    _records = [
        {
            id: 1,
            name: "Chocolate",
            attribute_id: 9,
        },
        {
            id: 2,
            name: "Vanilla",
            attribute_id: 9,
            price_extra: 5,
        },
        {
            id: 3,
            name: "Yes",
            is_custom: true,
            attribute_id: 10,
        },
    ];
}
