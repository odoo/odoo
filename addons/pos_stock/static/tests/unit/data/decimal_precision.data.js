import { patch } from "@web/core/utils/patch";
import { DecimalPrecision } from "@point_of_sale/../tests/unit/data/decimal_precision.data";

patch(DecimalPrecision, {
    _records: [
        ...DecimalPrecision._records,
        {
            id: 5,
            name: "Stock Weight",
            digits: 2,
        },
    ],
});
