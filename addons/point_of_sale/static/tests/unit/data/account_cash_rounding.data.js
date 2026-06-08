import { models } from "@web/../tests/web_test_helpers";

export class AccountCashRounding extends models.ServerModel {
    _name = "account.cash.rounding";

    _load_pos_data_fields() {
        return [];
    }
}
