import { models } from "@web/../tests/web_test_helpers";


export class SaleOrder extends models.ServerModel {
    _name = "sale.order";

    _records = [
        {
            id: 1,
            name: "first record",
            order_line: [],
        },
    ];
}
