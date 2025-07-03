import { ResCountry as WebResCountry } from "@web/../tests/_framework/mock_server/mock_models/res_country";

export class ResCountry extends WebResCountry {
    _name = "res.country";

    _load_pos_data_fields() {
        return ["id", "name", "code", "vat_label"];
    }

    _records = [
        ...WebResCountry.prototype.constructor._records,
        {
            id: 233,
            name: "United States",
            code: "US",
            vat_label: "",
        },
    ];
}
