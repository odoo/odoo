import { models } from "@web/../tests/web_test_helpers";

export class PosPayment extends models.ServerModel {
    _name = "pos.payment";

    _load_pos_data_fields() {
        return [];
    }
}
