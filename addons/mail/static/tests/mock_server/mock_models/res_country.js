import { webModels } from "@web/../tests/web_test_helpers";

export class ResCountry extends webModels.ResCountry {
    /** @param {number[]} ids */
    _to_store(ids, store) {
        for (const country of this.browse(ids)) {
            const [data] = this._read_format(country.id, ["code"], false);
            store.add(this.browse(country.id), data);
        }
    }
}
