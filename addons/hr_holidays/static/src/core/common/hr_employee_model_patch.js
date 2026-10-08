import { HrEmployee } from "@hr/core/common/hr_employee_model";
import { patchModel } from "@mail/model/export";

import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { toLocaleDateString } from "@web/core/l10n/dates";

export const hrEmployeePatch = patchModel(HrEmployee, {
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
});
