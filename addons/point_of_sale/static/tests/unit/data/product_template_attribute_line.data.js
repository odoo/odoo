import { models } from "@web/../tests/web_test_helpers";

export class ProductTemplateAttributeLine extends models.ServerModel {
    _name = "product.template.attribute.line";

    _load_pos_data_fields() {
        return ["display_name", "attribute_id", "product_template_value_ids"];
    }
}
