import { Component, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

export class KioskGreetings extends Component {
    static template = "hr_attendance.public_kiosk_greetings";
    static props = {
        employeeData: { type: Object },
        kioskReturn: { type: Function },
        kioskContinueBreak: { type: Function, optional: true },
    };

    setup() {
        this.formatDateTime = registry.category("formatters").get("datetime");
        this.formatFloatTime = registry.category("formatters").get("float_time");
        this.kiosk_delay = setTimeout(() => {
            this.props.kioskReturn(true);
        }, this.props.employeeData.kiosk_delay);
        onWillDestroy(() => this.clearKioskDelay());
    }

    clearKioskDelay() {
        clearTimeout(this.kiosk_delay);
        this.kiosk_delay = null;
    }

    continueBreak() {
        this.clearKioskDelay();
        this.props.kioskContinueBreak?.();
    }

    get employeeName() {
        return this.props.employeeData.employee_name;
    }

    get employeeAvatar() {
        return this.props.employeeData.employee_avatar;
    }

    get hoursToday() {
        return this.formatFloatTime(this.props.employeeData.hours_today);
    }

    get attendance() {
        return this.props.employeeData.attendance;
    }

    get checkInTime() {
        return this.formatDateTime(
            this.attendance.check_in && deserializeDateTime(this.attendance.check_in)
        );
    }

    get checkOutTime() {
        return this.formatDateTime(
            this.attendance.check_out && deserializeDateTime(this.attendance.check_out)
        );
    }

    get isCheckOut() {
        return Boolean(this.attendance.check_out);
    }

    get showContinueOptions() {
        return this.isCheckOut && this.props.employeeData.break_management_enabled;
    }

    get greetingTitle() {
        return this.isCheckOut ? _t("Goodbye") : _t("Welcome");
    }

    get statusAlertClass() {
        return this.isCheckOut ? "alert-danger" : "alert-success";
    }

    get statusMessage() {
        return this.isCheckOut
            ? sprintf(_t("Checked out at %s"), this.checkOutTime)
            : sprintf(_t("Checked in at %s"), this.checkInTime);
    }

    get isEmployeeSingleCheckIn() {
        return this.props.employeeData.is_employee_single_checkin;
    }

    get breakDuration() {
        return this.props.employeeData.break_duration
            ? this.formatFloatTime(this.props.employeeData.break_duration)
            : false;
    }

    get attendanceWorkedHours() {
        return this.formatFloatTime(this.props.employeeData.attendance_worked_hours || 0);
    }

    get hasTimesheet() {
        return Boolean(this.props.employeeData.has_timesheet);
    }

    get secondarySummaryLabel() {
        return this.isCheckOut ? _t("Hours Today") : _t("Hours Previously Today");
    }

    get overtimeToday() {
        if (!this.props.employeeData.display_overtime) {
            return false;
        }
        return this.formatFloatTime(this.props.employeeData.overtime_today);
    }

    get totalOvertime() {
        if (!this.props.employeeData.display_overtime) {
            return false;
        }
        return this.formatFloatTime(this.props.employeeData.total_overtime);
    }
}
