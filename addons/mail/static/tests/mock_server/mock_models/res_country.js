import { webModels } from "@web/../tests/web_test_helpers";

export class ResCountry extends webModels.ResCountry {
    get _to_store_defaults() {
        return ["code"];
    }
}
