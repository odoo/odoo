import { models } from "@web/../tests/web_test_helpers";

export class PosPackOperationLot extends models.ServerModel {
    _name = "pos.pack.operation.lot";

    _load_pos_data_fields() {
        return ["lot_name", "pos_order_line_id", "write_date"];
    }
}
