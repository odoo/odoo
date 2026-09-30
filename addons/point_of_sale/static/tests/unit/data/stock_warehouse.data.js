import { models } from "@web/../tests/web_test_helpers";

export class StockWarehouse extends models.ServerModel {
    _name = "stock.warehouse";

    _load_pos_data_fields() {
        return [];
    }
}
