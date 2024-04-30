import { fields, models } from "@web/../tests/web_test_helpers";

export class AccountMove extends models.Model {
    _name = "account.move";

    name = fields.Char();
}
