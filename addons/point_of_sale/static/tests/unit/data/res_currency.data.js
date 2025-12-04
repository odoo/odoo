import { webModels } from "@web/../tests/web_test_helpers";

export class ResCurrency extends webModels.ResCurrency {
    _name = "res.currency";

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "symbol",
            "position",
            "rounding",
            "rate",
            "decimal_places",
            "iso_numeric",
        ];
    }

    _records = [
        {
            id: 1,
            name: "USD",
            symbol: "$",
            position: "before",
            rounding: 0.01,
            rate: 1.0,
            decimal_places: 2,
            iso_numeric: 840,
        },
        {
            id: 125,
            name: "EUR",
            symbol: "€",
            position: "after",
            rounding: 0.01,
            rate: 1.0,
            decimal_places: 2,
            iso_numeric: 978,
        },
        ...webModels.ResCurrency._records.filter((record) => record.id !== 1),
    ];
}
