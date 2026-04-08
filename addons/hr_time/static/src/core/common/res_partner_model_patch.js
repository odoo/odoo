import { ResPartner } from "@mail/core/common/res_partner_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.main_user_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },
};
patch(ResPartner.prototype, resPartnerPatch);
