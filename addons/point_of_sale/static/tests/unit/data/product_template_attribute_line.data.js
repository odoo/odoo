import { models } from "@web/../tests/web_test_helpers";

export class ProductTemplateAttributeLine extends models.ServerModel {
    _name = "product.template.attribute.line";

    _load_pos_data_fields() {
        return ["display_name", "attribute_id", "product_template_value_ids"];
    }

    _records = [
        {
            id: 1,
            attribute_id: 9,
            product_template_value_ids: [1, 2],
        },
        {
            id: 2,
            attribute_id: 10,
            product_template_value_ids: [3],
        },
    ];
}
