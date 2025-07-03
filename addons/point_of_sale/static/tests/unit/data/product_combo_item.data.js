import { models } from "@web/../tests/web_test_helpers";

export class ProductComboItem extends models.ServerModel {
    _name = "product.combo.item";

    _load_pos_data_fields() {
        return ["id", "combo_id", "product_id", "extra_price"];
    }
}
