import { models } from "@web/../tests/web_test_helpers";

export class ResLang extends models.ServerModel {
    _name = "res.lang";

    get _to_store_defaults() {
        return ["name"];
    }
}
