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
        const employee_id = this.employee_id || this.main_user_id?.employee_id;
        if (!employee_id?.leave_date_to) {
            return "";
        }
        return getOutOfOfficeDateEndText(employee_id.leave_date_to);
    },
});
