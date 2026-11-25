import { fields, models } from "@web/../tests/web_test_helpers";

export class HrLeaveAllocation extends models.Model {
    _name = "hr.leave.allocation";

    name = fields.Char();

    has_requestable_work_entry_type() {
        return true;
    }
}
