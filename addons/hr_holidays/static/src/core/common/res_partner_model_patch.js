import { ResPartner } from "@mail/core/common/res_partner_model";
import { patchModel } from "@mail/model/export";

export const resPartnerPatch = patchModel(ResPartner, {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.main_user_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },
});
