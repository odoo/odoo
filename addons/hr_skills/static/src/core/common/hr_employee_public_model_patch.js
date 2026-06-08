import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { HrEmployeePublic } from "@hr/core/common/hr_employee_public_model";

patch(HrEmployeePublic.prototype, {
    setup() {
        super.setup();
        this.employee_skill_ids = fields.Many("hr.employee.skill");
    },
});
