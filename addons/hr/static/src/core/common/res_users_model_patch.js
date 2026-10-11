import { fields } from "@mail/model/misc";
import { ResUsers } from "@mail/core/common/res_users_model";
import { patchModel } from "@mail/model/export";

export const resUsersPatch = patchModel(ResUsers, {
    setup() {
        super.setup();
        this.all_employee_ids = fields.Many("hr.employee", { inverse: "user_id" });
        this.employee_id = this.computed(() =>
            this.store.getRelevantEmployee(this.all_employee_ids)
        );
    },
});
