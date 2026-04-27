import { fields, models } from "@web/../tests/web_test_helpers";

export class BarcodeRule extends models.Model {
    name = fields.Char();
    _records = [{ id: 1, name: "rule" }];
}
