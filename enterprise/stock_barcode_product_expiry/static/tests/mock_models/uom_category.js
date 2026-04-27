import { fields, models } from "@web/../tests/web_test_helpers";

export class UoMCategory extends models.Model {
    _name = "uom.category";
    name = fields.Char();
    _records = [{ id: 1, name: "Unit" }];
}
