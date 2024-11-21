import { fields, models } from "@web/../tests/web_test_helpers";

export class HrLeaveType extends models.Model {
    _name = "hr.leave.type";

    id = fields.Integer();
    name = fields.Char();

    _records = [
        {
            id: 55,
            name: "Legal Leave",
        },
        {
            id: 65,
            name: "Unpaid Leave",
        },
    ];
}
