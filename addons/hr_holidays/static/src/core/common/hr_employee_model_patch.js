import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").HrEmployee} */
const hrEmployeePatch = {
    setup() {
        super.setup();
        this.leave_date_to = fields.Date();
    },
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        if (!this.leave_date_to) {
            return "";
        }
        const foptions = { ...DateTime.DATE_MED };
        if (DateTime.now().hasSame(this.leave_date_to, "year")) {
            foptions.year = undefined;
        }
        const fdate = this.leave_date_to.toLocaleString(foptions);
        return _t("Back on %(date)s", { date: fdate });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
