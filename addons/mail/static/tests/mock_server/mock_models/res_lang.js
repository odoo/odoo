import { models } from "@web/../tests/web_test_helpers";

export class ResLang extends models.ServerModel {
    _name = "res.lang";

    get_installed() {
        return this._filter([])
            .sort((a, b) => a.name.localeCompare(b.name))
            .map((lang) => [lang.code, lang.name]);
    }
}
