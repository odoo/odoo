import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { HrEmployee } from "@hr/core/common/hr_employee_model";

patch(HrEmployee.prototype, {
    setup() {
        super.setup();
        this.employee_skill_ids = fields.Many("hr.employee.skill");
    },
});
