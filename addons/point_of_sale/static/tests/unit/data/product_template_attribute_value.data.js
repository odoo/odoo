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
            "excluded_value_ids",
        ];
    }

    _load_pos_data_dependencies() {
        return ["product.attribute"];
    }
    _records = [
        {
            id: 5,
            name: "Chocolate",
            attribute_id: 10,
            attribute_line_id: 3,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 6,
            name: "Vanilla",
            attribute_id: 10,
            attribute_line_id: 3,
            price_extra: 5,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 7,
            name: "Yes",
            is_custom: true,
            attribute_id: 11,
            attribute_line_id: 4,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 8,
            name: "S",
            attribute_id: 7,
            attribute_line_id: 5,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 9,
            name: "M",
            attribute_id: 7,
            attribute_line_id: 5,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 10,
            name: "Standard",
            attribute_id: 12,
            attribute_line_id: 6,
            write_date: "2023-06-01 10:00:00",
        },
        {
            id: 11,
            name: "Sprinkles",
            is_custom: false,
            attribute_id: 13,
            attribute_line_id: 7,
        },
        {
            id: 12,
            name: "Male",
            is_custom: false,
            attribute_id: 8,
            attribute_line_id: 108,
        },
    ];
}
