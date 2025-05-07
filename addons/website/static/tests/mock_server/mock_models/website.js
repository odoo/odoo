import { models } from "@web/../tests/web_test_helpers";

export class Website extends models.ServerModel {
    _name = "website";

    /** @param {number[]} ids */
    _to_store(ids, store) {
        for (const website of this.browse(ids)) {
            const [data] = this._read_format(website.id, ["name"]);
            store.add(this.browse(website.id), data);
        }
    }
}
