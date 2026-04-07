import { models } from "@web/../tests/web_test_helpers";

export class ProductTemplateAttributeLine extends models.ServerModel {
    _name = "product.template.attribute.line";

    _load_pos_data_fields() {
        return ["display_name", "attribute_id", "product_template_value_ids"];
    }

    _records = [
        {
            id: 3,
            attribute_id: 10,
            product_template_value_ids: [5, 6],
        },
        {
            id: 4,
            attribute_id: 11,
            product_template_value_ids: [7],
        },
    ];
}
