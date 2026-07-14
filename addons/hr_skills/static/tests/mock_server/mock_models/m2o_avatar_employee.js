import { fields, models } from "@web/../tests/web_test_helpers";

export class M2oAvatarEmployee extends models.Model {
    _name = "m2o.avatar.employee";

    employee_id = fields.Many2one({ string: "Employee", relation: "hr.employee" });
}
