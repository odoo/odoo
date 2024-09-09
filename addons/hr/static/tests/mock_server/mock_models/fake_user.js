import { fields, models } from "@web/../tests/web_test_helpers";

export class FakeUser extends models.Model {
    _name = "fake.user";

    name = fields.Char({ string: "Name" });
    lang = fields.Char({ string: "Lang" });
}
