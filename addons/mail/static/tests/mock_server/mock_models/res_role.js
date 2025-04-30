import { fields, models } from "@web/../tests/web_test_helpers";

export class ResRole extends models.ServerModel {
    _name = "res.role";

    name = fields.Char();
}
