import { models } from "@web/../tests/web_test_helpers";

export class IapAccount extends models.ServerModel {
    _name = "iap.account";

    get_credits_url() {
        return true;
    }
}
