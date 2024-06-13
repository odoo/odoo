import { fields, models } from "@web/../tests/web_test_helpers";

export class M2XAVatarEmployee extends models.Model {
    _name = "m2x.avatar.employee";

    employee_id = fields.Many2one({ relation: "hr.employee.public" });
    employee_ids = fields.Many2many({ relation: "hr.employee.public" });
}
