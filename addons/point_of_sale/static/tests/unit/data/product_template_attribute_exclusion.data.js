import { models } from "@web/../tests/web_test_helpers";

export class ProductTemplateAttributeExclusion extends models.ServerModel {
    _name = "product.template.attribute.exclusion";

    _load_pos_data_fields() {
        return ["value_ids", "product_template_attribute_value_id"];
    }
}
