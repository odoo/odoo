import { Component, useProps } from "@odoo/owl";
import { formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Warns when the browser, which displays the attendance, is not on the employee's clock:
 * the field holds the employee's timezone, the browser's is known here only.
 */
export class AttendanceTzWarningField extends Component {
    static template = "hr_attendance.AttendanceTzWarningField";
    props = useProps(standardFieldProps);

    /**
     * The browser's timezone, in which the form displays the hours.
     *
     * @returns {string}
     */
    get browserTz() {
        return luxon.Settings.defaultZone.name;
    }

    /**
     * The attendance in the employee's timezone, when its offset differs from the user's browser's at
     * the check in (two names with the same offset, e.g. Paris and Brussels, do not warn).
     *
     * @returns {string}
     */
    get warning() {
        const { check_in: checkIn, check_out: checkOut, employee_id: employee } = this.props.record.data;
        const tz = this.props.record.data[this.props.name]; // field => employee_tz
        if (!tz || !checkIn) {
            return "";
        }
        const employeeCheckIn = checkIn.setZone(tz);
        if (!employeeCheckIn.isValid || employeeCheckIn.offset === checkIn.offset) {
            return "";
        }
        const values = {
            employee: employee?.display_name,
            check_in: formatDateTime(checkIn, { tz }),
            tz,
        };
        if (!checkOut) {
            return _t("For %(employee)s, this is %(check_in)s (%(tz)s).", values);
        }
        return _t("For %(employee)s, this is %(check_in)s – %(check_out)s (%(tz)s).", {
            ...values,
            check_out: formatDateTime(checkOut, { tz }),
        });
    }
}

export const attendanceTzWarningField = {
    component: AttendanceTzWarningField,
    supportedTypes: ["char"],
};

registry.category("fields").add("attendance_tz_warning", attendanceTzWarningField);
