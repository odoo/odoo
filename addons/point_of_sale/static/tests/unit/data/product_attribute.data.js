import { models } from "@web/../tests/web_test_helpers";

export class ProductAttribute extends models.ServerModel {
    _name = "product.attribute";
    _order = "id";

    _load_pos_data_fields() {
        return [
            "name",
            "display_type",
            "template_value_ids",
            "attribute_line_ids",
            "create_variant",
        ];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "color",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 2,
            name: "gender",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 3,
            name: "material",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 4,
            name: "pattern",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 5,
            name: "manufacturer",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 6,
            name: "brand",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 7,
            name: "size",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 8,
            name: "age group",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
