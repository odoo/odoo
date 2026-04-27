import { fields, models } from "@web/../tests/web_test_helpers";

export class Fake extends models.Model {
    _name = "fake";

    phone = fields.Char({ string: "Phone Number" });
}
