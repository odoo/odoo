import { models } from "@web/../tests/web_test_helpers";

export class ResLang extends models.ServerModel {
    _name = "res.lang";

    _to_store(ids, store) {
        for (const lang of this.browse(ids)) {
            const [data] = this._read_format(lang.id, ["name"]);
            store.add(this.browse(lang.id), data);
        }
    }
}
