import { models } from "@web/../tests/web_test_helpers";

export class ProductCombo extends models.ServerModel {
    _name = "product.combo";

    _load_pos_data_fields() {
        return ["id", "name", "combo_item_ids", "base_price", "qty_free", "qty_max"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        {
            id: 1,
            name: "Chairs Combo",
            combo_item_ids: [1, 2],
            base_price: 100,
            qty_free: 0,
            qty_max: 10,
            write_date: "2025-01-01 10:00:00",
        },
        {
            id: 2,
            name: "Desks Combo",
            combo_item_ids: [3, 4],
            base_price: 200,
            qty_free: 1,
            qty_max: 1,
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
