import { fields, models } from "@web/../tests/web_test_helpers";

export class UoM extends models.Model {
    _name = "uom.uom";
    name = fields.Char();
    category_id = fields.Many2one({ relation: "uom.category" });
    factor = fields.Float();
    rounding = fields.Float();
    _records = [
        {
            id: 4,
            name: "Units",
            category_id: 1,
            factor: 1.0,
            rounding: 0.01,
        },
    ];
}
