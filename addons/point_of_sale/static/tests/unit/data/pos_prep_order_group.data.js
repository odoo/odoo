import { models } from "@web/../tests/web_test_helpers";

export class PosPrepOrderGroup extends models.ServerModel {
    _name = "pos.prep.order.group";

    _load_pos_data_fields() {
        return [];
    }
}
