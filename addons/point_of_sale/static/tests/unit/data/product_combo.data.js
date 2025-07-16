import { models } from "@web/../tests/web_test_helpers";

export class ProductCombo extends models.ServerModel {
    _name = "product.combo";

    _load_pos_data_fields() {
        return ["id", "name", "combo_item_ids", "base_price", "qty_free", "qty_max"];
    }
}
