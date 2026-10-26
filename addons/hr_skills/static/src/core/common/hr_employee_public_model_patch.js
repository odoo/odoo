import { fields } from "@mail/model/misc";
import { HrEmployeePublic } from "@hr/core/common/hr_employee_public_model";
import { patchModel } from "@mail/model/export";

export const hrEmployeePublicPatch = patchModel(HrEmployeePublic, {
    setup() {
        super.setup();
        this.employee_skill_ids = fields.Many("hr.employee.skill");
    },
});
