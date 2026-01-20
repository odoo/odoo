import { hrModels } from "@hr/../tests/hr_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class HrEmployee extends hrModels.HrEmployee {
    _name = "hr.employee";

    name = fields.Char();
    leave_date_to = fields.Date();
    leave_date_from = fields.Datetime();
    request_date_from_period = fields.Selection({
        selection: [
            ["am", "Morning"],
            ["pm", "Afternoon"],
        ],
    });
    next_working_day_on_leave = fields.Date();
    user_id = fields.Many2one({ relation: "res.users" });

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
