import { patch } from "@web/core/utils/patch";
import { fields } from "@mail/model/misc";
import { ResUsers } from "@mail/core/common/res_users_model";

patch(ResUsers.prototype, {
    setup() {
        super.setup();
        this.all_employee_ids = fields.Many("hr.employee", { inverse: "user_id" });
        this.employee_id = fields.One("hr.employee", {
            compute() {
                return this.store.getRelevantEmployee(this.all_employee_ids);
            },
        });
    },
});
