import { ResPartner } from "@mail/core/common/res_partner_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ResPartner} */
const resPartnerPatch = {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const employee = this.employee_id || this.main_user_id?.employee_id;
        return employee?.outOfOfficeDateEndText ?? "";
    },

    statusSubtitleParts() {
        const parts = super.statusSubtitleParts();
        // the meeting status of calendar takes priority over the time off
        if (!this.outOfOfficeDateEndText || this.inMeetingEndText) {
            return parts;
        }
        return [
            { class: "text-warning fw-bold opacity-75", text: this.outOfOfficeDateEndText },
            ...parts,
        ];
    },
};
patch(ResPartner.prototype, resPartnerPatch);
