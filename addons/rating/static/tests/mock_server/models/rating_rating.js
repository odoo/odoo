import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";

export class RatingRating extends models.ServerModel {
    _name = "rating.rating";

    res_model = fields.Char({ string: "Related Document Model", related: false }); // FIXME: related removed otherwise it cannot be set properly

    /**
     * @param {Number[]} ids
     * @returns {Record<string, ModelRecord>}
     */
    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;
        if (!fields) {
            fields = ["rating", "rating_image_url", "rating_text"];
        }
        store.add(this._name, this._read_format(ids, fields, false));
    }
}
