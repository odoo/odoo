import { fields, models } from "@web/../tests/web_test_helpers";

export class M2xAvatarEmployee extends models.Model {
    _name = "m2x.avatar.employee";

    employee_id = fields.Many2one({ string: "Employee", relation: "hr.employee.public" });
    employee_ids = fields.Many2many({ string: "Employees", relation: "hr.employee.public" });
}
