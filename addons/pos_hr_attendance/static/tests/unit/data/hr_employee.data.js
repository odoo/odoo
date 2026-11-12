import { patch } from "@web/core/utils/patch";
import { HrEmployee } from "@pos_hr/../tests/unit/data/hr_employee.data";

patch(HrEmployee.prototype, {
    get_pos_attendance_states(employeeIds) {
        return Object.fromEntries(
            employeeIds.map((id) => [id, id === 3 ? "checked_in" : "checked_out"])
        );
    },
});
