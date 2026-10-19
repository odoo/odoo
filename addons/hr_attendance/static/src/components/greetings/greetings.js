import { Component, computed, onWillDestroy, t, useProps } from "@odoo/owl";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { formatDateTime, formatFloatTime } from "@web/views/fields/formatters";

export class KioskGreetings extends Component {
    static template = "hr_attendance.public_kiosk_greetings";
    props = useProps({
        employeeData: t.object(),
        kioskReturn: t.function(),
        kioskContinueBreak: t.function().optional(() => () => {}),
    });

    setup() {
        this.kioskDelay = setTimeout(() => {
            this.props.kioskReturn(true);
        }, this.props.employeeData.kiosk_delay);
        onWillDestroy(() => this.clearKioskDelay());
    }

    get attendance() {
        return this.props.employeeData.attendance;
    }

    get isCheckOut() {
        return Boolean(this.attendance.check_out);
    }

    checkInTime = computed(() =>
        this.attendance.check_in ? formatDateTime(deserializeDateTime(this.attendance.check_in)) : ""
    );
    checkOutTime = computed(() =>
        this.attendance.check_out ? formatDateTime(deserializeDateTime(this.attendance.check_out)) : ""
    );
    hoursToday = computed(() => formatFloatTime(this.props.employeeData.hours_today));
    overtimeToday = computed(
        () =>
            this.props.employeeData.display_overtime &&
            formatFloatTime(this.props.employeeData.overtime_today)
    );
    totalOvertime = computed(
        () =>
            this.props.employeeData.display_overtime &&
            formatFloatTime(this.props.employeeData.total_overtime)
    );

    clearKioskDelay() {
        clearTimeout(this.kioskDelay);
    }

    continueBreak() {
        this.clearKioskDelay();
        this.props.kioskContinueBreak();
    }
}
