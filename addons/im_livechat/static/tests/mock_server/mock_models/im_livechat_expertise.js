import { getKwArgs, models } from "@web/../tests/web_test_helpers";

export class Im_LivechatExpertise extends models.ServerModel {
    _name = "im_livechat.expertise";

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        if (!fields) {
            fields = [];
        }
        for (const LivechatExpertise of this.browse(ids)) {
            const [res] = this._read_format(LivechatExpertise.id, fields, false);
            store.add(this.browse(LivechatExpertise.id), res);
        }
    }
}
