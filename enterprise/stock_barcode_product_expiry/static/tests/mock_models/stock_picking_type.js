import { fields, models } from "@web/../tests/web_test_helpers";

export class StockPickingType extends models.Model {
    name = fields.Char();
    show_reserved_sns = fields.Boolean();
    use_create_lots = fields.Boolean();
    _records = [{ id: 1, name: "TEST", show_reserved_sns: false, use_create_lots: true }];
}
