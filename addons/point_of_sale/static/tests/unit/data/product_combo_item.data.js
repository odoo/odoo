import { models } from "@web/../tests/web_test_helpers";

export class ProductComboItem extends models.ServerModel {
    _name = "product.combo.item";

    _load_pos_data_fields() {
        return ["id", "combo_id", "product_id", "extra_price"];
    }

    _records = [
        {
            id: 1,
            combo_id: 1,
            product_id: 8,
            extra_price: 0,
        },
        {
            id: 2,
            combo_id: 1,
            product_id: 9,
            extra_price: 35,
        },
        {
            id: 3,
            combo_id: 2,
            product_id: 10,
            extra_price: 0,
        },
        {
            id: 4,
            combo_id: 2,
            product_id: 11,
            extra_price: 50,
        },
    ];
}
