import { fields, models } from "@web/../tests/web_test_helpers";

export class Visitor extends models.Model {
    _name = "visitor";

    mobile = fields.Char();
}
