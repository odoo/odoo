import { models } from "@web/../tests/web_test_helpers";

export class ResLang extends models.ServerModel {
    _name = "res.lang";

    _load_pos_data_fields() {
        return ["id", "name", "code", "flag_image_url", "display_name"];
    }

    _records = [
        {
            id: 1,
            name: "English (US)",
            code: "en_US",
            flag_image_url: "/base/static/img/country_flags/us.png",
            display_name: "English (US)",
        },
    ];
}
