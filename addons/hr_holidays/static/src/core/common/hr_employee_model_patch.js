import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { fields } from "@mail/model/misc";

import { deserializeDateTime } from "@web/core/l10n/dates";
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
        const dt =
            typeof this.leave_date_to === "string"
                ? deserializeDateTime(this.leave_date_to)
                : this.leave_date_to;
        if (DateTime.now().hasSame(dt, "year")) {
            foptions.year = undefined;
        }
        const fdate = dt.toLocaleString(foptions);
        return _t("Back on %(date)s", { date: fdate });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
