import { fields, models } from "@web/../tests/web_test_helpers";

export class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    department_id = fields.Many2one({ relation: "hr.department" });

    _records = [
        {
            id: 100,
            name: "Richard",
            department_id: 11,
        },
        {
            id: 200,
            name: "Jane",
            department_id: 11,
        },
    ];
}
