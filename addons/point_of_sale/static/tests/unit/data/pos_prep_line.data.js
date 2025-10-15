import { models } from "@web/../tests/web_test_helpers";

export class PosPrepLine extends models.ServerModel {
    _name = "pos.prep.line";

    _load_pos_data_fields() {
        return [];
    }
}
