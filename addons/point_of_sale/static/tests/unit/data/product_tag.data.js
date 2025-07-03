import { models } from "@web/../tests/web_test_helpers";

export class ProductTag extends models.ServerModel {
    _name = "product.tag";

    _load_pos_data_fields() {
        return ["name", "pos_description", "color", "has_image", "write_date"];
    }
}
