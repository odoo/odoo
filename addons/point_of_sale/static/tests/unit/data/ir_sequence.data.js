import { models } from "@web/../tests/web_test_helpers";

export class IrSequence extends models.ServerModel {
    _name = "ir.sequence";

    _load_pos_data_fields() {
        return [];
    }
}
