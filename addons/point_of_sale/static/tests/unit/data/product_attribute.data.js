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

    _records = [
        {
            id: 1,
            name: "color",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 2,
            name: "gender",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 3,
            name: "material",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 4,
            name: "pattern",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 5,
            name: "manufacturer",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 6,
            name: "brand",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 7,
            name: "size",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
        {
            id: 8,
            name: "age group",
            display_type: "radio",
            template_value_ids: [],
            attribute_line_ids: [],
            create_variant: "always",
        },
    ];
}
