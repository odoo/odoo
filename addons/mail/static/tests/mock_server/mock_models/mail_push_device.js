import { models } from "@web/../tests/web_test_helpers";

export class MailPushDevice extends models.ServerModel {
    _name = "mail.push.device";
    get_web_push_vapid_public_key() {
        return "BPNWmvXxxCOd-QBNMZeF2pL0CAFcZebRRZJzco-s2C2oadl9kQU59hNJW4IscNmzs9L7q9ID9cLCzSIH1vZpqBY";
    }
    unregister_devices() {}
}
