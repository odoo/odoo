import { ResUsers } from "@mail/core/common/res_users_model";
import { patchModel } from "@mail/model/export";

export const resUsersPatch = patchModel(ResUsers, {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.partner_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },
});
