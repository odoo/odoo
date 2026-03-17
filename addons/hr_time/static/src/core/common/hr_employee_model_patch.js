import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { toLocaleDateString } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

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
        const fdate = toLocaleDateString(this.leave_date_to);
        return _t("Back on %(date)s", { date: fdate });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
