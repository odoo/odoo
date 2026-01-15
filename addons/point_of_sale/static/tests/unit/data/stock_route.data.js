import { models } from "@web/../tests/web_test_helpers";

export class StockRoute extends models.ServerModel {
    _name = "stock.route";

    _load_pos_data_fields() {
        return [];
    }
}
