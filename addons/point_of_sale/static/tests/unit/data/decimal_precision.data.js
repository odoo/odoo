import { models } from "@web/../tests/web_test_helpers";

export class DecimalPrecision extends models.ServerModel {
    _name = "decimal.precision";

    _load_pos_data_fields() {
        return ["id", "name", "digits"];
    }

    _records = [
        {
            id: 1,
            name: "Product Unit",
            digits: 2,
        },
        {
            id: 2,
            name: "Percentage Analytic",
            digits: 2,
        },
        {
            id: 3,
            name: "Product Price",
            digits: 2,
        },
        {
            id: 4,
            name: "Discount",
            digits: 2,
        },
        {
            id: 5,
            name: "Stock Weight",
            digits: 2,
        },
        {
            id: 6,
            name: "Volume",
            digits: 2,
        },
        {
            id: 7,
            name: "Payment Terms",
            digits: 6,
        },
    ];
}
