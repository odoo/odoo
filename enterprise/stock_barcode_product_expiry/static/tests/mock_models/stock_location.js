import { fields, models } from "@web/../tests/web_test_helpers";

export class StockLocation extends models.Model {
    name = fields.Char();
    barcode = fields.Char();
    parent_path = fields.Char();
    _records = [
        {
            id: 5,
            barcode: "WH-STOCK 1",
            display_name: "WH/STOCK 1",
            name: "STOCK 1",
            parent_path: "1/7",
        },
        {
            id: 6,
            barcode: "WH-STOCK 2",
            display_name: "WH/STOCK 2",
            name: "STOCK 2",
            parent_path: "1/7/8",
        },
    ];
}
