import { models } from "@web/../tests/web_test_helpers";

export class ProductPricelist extends models.ServerModel {
    _name = "product.pricelist";

    _load_pos_data_fields() {
        return ["id", "name", "display_name", "item_ids"];
    }

    _records = [
        {
            id: 1,
            name: "Test Pricelist A",
            display_name: "Test Pricelist A (USD)",
            item_ids: [1],
        },
        {
            id: 2,
            name: "Test Pricelist B",
            display_name: "Test Pricelist B (USD)",
            item_ids: [1],
        },
    ];
}
