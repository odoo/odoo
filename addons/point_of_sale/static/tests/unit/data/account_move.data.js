import { models } from "@web/../tests/web_test_helpers";

export class AccountMove extends models.ServerModel {
    _name = "account.move";

    _load_pos_data_fields() {
        return ["id"];
    }
}
