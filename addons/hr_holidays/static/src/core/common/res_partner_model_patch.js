import { ResPartner } from "@mail/core/common/res_partner_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.main_user_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },

    /** @returns {string} */
    get statusSubtitle() {
        return this.main_user_id?.status_message || this.outOfOfficeDateEndText;
    },

    /** @returns {string} */
    get statusSubtitleClass() {
        return this.main_user_id?.status_message
            ? "text-info fw-bold text-muted"
            : "text-warning fw-bold opacity-75";
    },
};
patch(ResPartner.prototype, resPartnerPatch);
