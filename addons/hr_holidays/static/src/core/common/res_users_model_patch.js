import { ResUsers } from "@mail/core/common/res_users_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResUsers} */
const resUsersPatch = {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.partner_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },
};
patch(ResUsers.prototype, resUsersPatch);
