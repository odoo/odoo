import { webModels } from "@web/../tests/web_test_helpers";

export class ResCountry extends webModels.ResCountry {
    _name = "res.country";

    _load_pos_data_fields() {
        return ["id", "name", "code", "vat_label"];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    _records = [
        ...webModels.ResCountry._records,
        {
            id: 233,
            name: "United States",
            code: "US",
            vat_label: "",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
