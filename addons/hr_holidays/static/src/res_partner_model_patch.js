import { ResPartner } from "@mail/core/common/res_partner_model";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @param {string} datetime */
export function getOutOfOfficeDateEndText(datetime) {
    const foptions = { ...DateTime.DATE_MED };
    const dt = typeof datetime === "string" ? deserializeDateTime(datetime) : datetime;
    if (dt.year === DateTime.now().year) {
        foptions.year = undefined;
    }
    const fdate = dt.toLocaleString(foptions);
    return _t("Back on %(date)s", { date: fdate });
}

patch(ResPartner.prototype, {
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        const leave_date_to = this.main_user_id?.employee_id?.leave_date_to;
        if (this.im_status.startsWith("leave_") && !leave_date_to) {
            return _t("On leave due to public holiday");
        }
        if (!leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(leave_date_to);
    },
});
