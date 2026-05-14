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
            id: 5,
            name: "Chocolate",
            attribute_id: 10,
        },
        {
            id: 6,
            name: "Vanilla",
            attribute_id: 10,
            price_extra: 5,
        },
        {
            id: 7,
            name: "Yes",
            is_custom: true,
            attribute_id: 11,
        },
        {
            id: 1001,
            attribute_id: 9,
            attribute_line_id: 101,
            product_attribute_value_id: 4,
            price_extra: 0,
            name: "Sauce",
            is_custom: false,
            html_color: false,
            image: false,
            exclude_for: [],
        },
        {
            id: 1002,
            attribute_id: 10,
            attribute_line_id: 102,
            product_attribute_value_id: 5,
            price_extra: 0,
            name: "Message",
            is_custom: true,
            html_color: false,
            image: false,
            exclude_for: [],
        },
    ];
}
