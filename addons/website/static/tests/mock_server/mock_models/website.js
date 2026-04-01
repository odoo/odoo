import { models } from "@web/../tests/web_test_helpers";

export class Website extends models.ServerModel {
    _name = "website";

    get _to_store_defaults() {
        return ["name"];
    }
}
