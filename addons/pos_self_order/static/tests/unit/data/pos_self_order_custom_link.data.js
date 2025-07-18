import { models } from "@web/../tests/web_test_helpers";

export class PosSelfOrderCustomLink extends models.ServerModel {
    _name = "pos_self_order.custom_link";

    _load_pos_data_fields() {
        return [];
    }
}
