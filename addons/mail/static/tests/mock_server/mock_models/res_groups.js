import { getKwArgs, webModels } from "@web/../tests/web_test_helpers";
export class ResGroups extends webModels.ResGroups {
    _inherit = ["res.groups"];

    /** @param {number[]} ids */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        for (const group of this.browse(ids)) {
            const [data] = this._read_format(group.id, fields, false);
            store.add(this.browse(group.id), data);
        }
    }
}
