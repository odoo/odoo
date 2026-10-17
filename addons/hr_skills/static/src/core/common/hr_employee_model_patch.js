import { fields } from "@mail/model/misc";
import { HrEmployee } from "@hr/core/common/hr_employee_model";
import { patchModel } from "@mail/model/export";

export const hrEmployeePatch = patchModel(HrEmployee, {
    setup() {
        super.setup();
        this.employee_skill_ids = fields.Many("hr.employee.skill");
    },
});
