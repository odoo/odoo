import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { toLocaleDateString } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").HrEmployee} */
const hrEmployeePatch = {
    setup() {
        super.setup();
        this.leave_back_datetime = fields.Datetime();
        this.leave_date_to = fields.Date();
    },
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        if (!this.leave_date_to) {
            return "";
        }
        if (
            this.leave_back_datetime &&
            this.leave_back_datetime.hasSame(this.store.startOfToday, "day")
        ) {
            return _t("Back at %(time)s", {
                time: this.leave_back_datetime.toLocaleString(DateTime.TIME_SIMPLE, {
                    locale: user.lang,
                }),
            });
        }
        const fdate = toLocaleDateString(this.leave_back_datetime || this.leave_date_to);
        return _t("Back on %(date)s", { date: fdate });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
