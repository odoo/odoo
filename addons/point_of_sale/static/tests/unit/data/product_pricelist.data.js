import { models } from "@web/../tests/web_test_helpers";

export class ProductPricelist extends models.ServerModel {
    _name = "product.pricelist";

    _load_pos_data_fields() {
        return ["id", "name", "display_name", "item_ids"];
    }

    _records = [
        {
            id: 1,
            name: "Test Pricelist",
            display_name: "Test Pricelist (USD)",
            item_ids: [1],
        },
    ];
}
