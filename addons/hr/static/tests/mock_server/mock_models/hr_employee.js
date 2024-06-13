import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    name = fields.Char();
}
