import { models } from "@web/../tests/web_test_helpers";

export class ProductCombo extends models.ServerModel {
    _name = "product.combo";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "combo_item_ids",
            "base_price",
            "qty_free",
            "qty_max",
            "is_upsell",
            "sequence",
        ];
    }

    _records = [
        {
            id: 1,
            name: "Chairs Combo",
            combo_item_ids: [1, 2],
            base_price: 100,
            is_upsell: true,
            qty_free: 0,
            qty_max: 10,
            sequence: 0,
        },
        {
            id: 2,
            name: "Desks Combo",
            combo_item_ids: [3, 4],
            base_price: 200,
            is_upsell: false,
            qty_free: 1,
            qty_max: 1,
            sequence: 1,
        },
        {
            id: 3,
            name: "Combo 3",
            combo_item_ids: [5, 6],
            base_price: 100,
            is_upsell: false,
            qty_free: 1,
            qty_max: 3,
            sequence: 2,
        },
        {
            id: 4,
            name: "Combo 4",
            combo_item_ids: [7, 8],
            base_price: 200,
            is_upsell: false,
            qty_free: 2,
            qty_max: 4,
            sequence: 3,
        },
        {
            id: 5,
            name: "Combo 5",
            combo_item_ids: [9, 10],
            base_price: 100,
            is_upsell: true,
            qty_free: 0,
            qty_max: 1,
            sequence: 4,
        },
        {
            id: 6,
            name: "Combo 6",
            combo_item_ids: [11, 12],
            base_price: 200,
            is_upsell: true,
            qty_free: 0,
            qty_max: 5,
            sequence: 5,
        },
    ];
}
