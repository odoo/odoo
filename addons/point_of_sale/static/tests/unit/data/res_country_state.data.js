import { models } from "@web/../tests/web_test_helpers";

export class ResCountryState extends models.ServerModel {
    _name = "res.country.state";

    _load_pos_data_fields() {
        return ["id", "name", "code", "country_id"];
    }

    _records = [
        {
            id: 69,
            name: "Armed Forces Europe",
            code: "AE",
            country_id: 233,
        },
    ];
}
