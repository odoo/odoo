import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { fields } from "@mail/model/misc";

import { _t } from "@web/core/l10n/translation";
import { toLocaleDateString } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

/** @type {import("models").HrEmployee} */
const hrEmployeePatch = {
    setup() {
        super.setup();
        this.leave_date_to = fields.Date();
        this.leave_date_from = fields.Datetime();
        /** @type {'am'|'pm'} */
        this.request_date_from_period;
        this.next_working_day_on_leave = fields.Date();
    },
    get outOfOfficeDateEndText() {
        if (this.next_working_day_on_leave) {
            const date = toLocaleDateString(this.next_working_day_on_leave);
            return _t("Out of office starting on %(date)s", { date });
        }
        if (this.leave_date_from) {
            if (
                DateTime.now().hasSame(this.leave_date_from, "day") &&
                (this.request_date_from_period === "pm" || this.leave_date_from.hour > 12)
            ) {
                const time = this.leave_date_from.toLocaleString(DateTime.TIME_SIMPLE);
                return _t("Out of office starting at %(time)s", { time });
            }
            if (DateTime.now().plus({ day: 1 }).hasSame(this.leave_date_from, "day")) {
                return _t("Out of office tomorrow");
            }
        }
        if (this.leave_date_to) {
            const date = toLocaleDateString(this.leave_date_to);
            return _t("Back on %(date)s", { date });
        }
        return "";
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
