import { fields, models } from "@web/../tests/web_test_helpers";

export class RatingRating extends models.ServerModel {
    _name = "rating.rating";

    res_model = fields.Char({ string: "Related Document Model", related: false }); // FIXME: related removed otherwise it cannot be set properly

    get _to_store_defaults() {
        return [
            "rating",
            "rating_image_url",
            "rating_text",
        ]
    }
}
