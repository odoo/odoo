import { HrEmployee } from "@hr/core/common/hr_employee_model";

import { Record } from "@mail/model/record";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const floatTime = registry.category("formatters").get("float_time");

const { DateTime } = luxon;

/** @type {import("models").HrEmployee} */
const hrEmployeePatch = {
    setup() {
        super.setup(...arguments);
        this.checkedIn = Record.attr(undefined, {
            compute() {
                return this.attendance_state === "checked_in";
            },
        });
        this.hoursPreviouslyToday = Record.attr(undefined, {
            compute() {
                return floatTime(this.hours_previously_today);
            },
        });
        this.hoursToday = Record.attr(undefined, {
            compute() {
                return floatTime(this.hours_today);
            },
        });
        this.isFirstAttendance = Record.attr(undefined, {
            compute() {
                return this.hours_previously_today === 0;
            },
        });
        this.lastAttendanceWorkedHours = Record.attr(undefined, {
            compute() {
                return floatTime(this.last_attendance_worked_hours);
            },
        });
        this.lastCheckIn = Record.attr(undefined, {
            compute() {
                return deserializeDateTime(this.last_check_in).toLocaleString(DateTime.TIME_SIMPLE);
            },
        });
    },
};
patch(HrEmployee.prototype, hrEmployeePatch);
