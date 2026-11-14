import { ResPartner } from "@mail/core/common/res_partner_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.main_user_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },

    statusSubtitle() {
        return super.statusSubtitle() || this.outOfOfficeDateEndText;
    },

    statusSubtitleClass() {
        return super.statusSubtitle()
            ? super.statusSubtitleClass()
            : "text-warning fw-bold opacity-75";
    },
};
patch(ResPartner.prototype, resPartnerPatch);
