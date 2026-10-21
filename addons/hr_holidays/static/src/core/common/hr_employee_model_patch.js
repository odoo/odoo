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
        this.leave_datetime_to = fields.Datetime();
    },
    /** @returns {boolean} */
    get isBackToday() {
        return Boolean(this.leave_datetime_to?.hasSame(this.store.startOfToday, "day"));
    },
    /** @returns {boolean} */
    get isOnLeave() {
        if (!this.leave_datetime_to) {
            return false;
        }
        // Back after today: on leave for the rest of the day, without reading the
        // minute, so that longer leaves are not rendered again every minute.
        if (this.leave_datetime_to > this.store.startOfToday.endOf("day")) {
            return true;
        }
        // Back today or earlier: on leave until the return time.
        const now = this.store.startOfMinute;
        return this.leave_datetime_to > now;
    },
    /** @returns {string} */
    get outOfOfficeDateEndText() {
        if (!this.isOnLeave) {
            return "";
        }
        if (this.isBackToday) {
            return _t("Back at %(time)s", {
                time: this.leave_datetime_to.toLocaleString(DateTime.TIME_SIMPLE, {
                    locale: user.lang,
                }),
            });
        }
        return _t("Back on %(date)s", { date: toLocaleDateString(this.leave_datetime_to) });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
