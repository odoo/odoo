import { models } from "@web/../tests/web_test_helpers";

export class AccountMove extends models.ServerModel {
    _name = "account.move";

    get_extra_print_items() {
        return [];
    }

}
