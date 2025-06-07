import { fields, models } from "@web/../tests/web_test_helpers";

export class HrDepartment extends models.Model {
    _name = "hr.department";

    id = fields.Integer();
    name = fields.Char();

    _records = [
        {
            id: 11,
            name: "R&D",
        },
    ];
}
