import { ResCurrency as WebResCurrency } from "@web/../tests/_framework/mock_server/mock_models/res_currency";

export class ResCurrency extends WebResCurrency {
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
        ...WebResCurrency.prototype.constructor._records.reduce((acc, record) => {
            if (record.id !== 1) {
                acc.push(record);
            }
            return acc;
        }, []),
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
    ];
}
