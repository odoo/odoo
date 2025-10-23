import { ResUsers } from "@mail/core/common/res_users_model";

import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

patch(ResUsers.prototype, {
    _compute_employee_id() {
        return (
            this.employee_ids.find(
                (employee) => employee.company_id?.id === user.activeCompany.id
            ) || this.employee_ids[0]
        );
    },
});
