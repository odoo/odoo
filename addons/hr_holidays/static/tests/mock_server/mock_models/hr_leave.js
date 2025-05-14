import { fields, models } from "@web/../tests/web_test_helpers";

export class HrLeave extends models.Model {
    _name = "hr.leave";

    id = fields.Integer();
    employee_id = fields.Many2one({
        relation: "hr.employee",
    });
    user_id = fields.Many2one({
        relation: "res.users"
    });
    department_id = fields.Many2one({
        relation: "hr.department",
    });
    date_from = fields.Datetime();
    date_to = fields.Datetime();
    holiday_status_id = fields.Many2one({
        relation: "hr.leave.type",
    });
    state = fields.Char();
    number_of_days = fields.Integer();
    number_of_hours = fields.Integer();
    leave_type_request_unit = fields.Selection({
        string: "Leave Type Request Unit",
        type: "selection",
        selection: [
            ["day", "Day"],
            ["half_day", "Half Day"],
            ["hour", "Hours"],
        ],
    });
    can_cancel = fields.Boolean();
    is_hatched = fields.Boolean();
    is_striked = fields.Boolean();
}
