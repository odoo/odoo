import {Component, onWillDestroy} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class KioskGreetings extends Component {
    static template = "hr_attendance.public_kiosk_greetings";
    static props = {
        employeeData: { type: Object },
        kioskReturn: { type: Function },
    };

    setup() {
        this.formatDateTime = registry.category("formatters").get("datetime");
        this.formatFloatTime = registry.category("formatters").get("float_time");
        this.employeeName = this.props.employeeData.employee_name;
        this.employeeAvatar = this.props.employeeData.employee_avatar;
        this.hoursToday = this.formatFloatTime(this.props.employeeData.hours_today);
        this.attendance = this.props.employeeData.attendance;
        this.check_in_time = this.formatDateTime(this.attendance.check_in && deserializeDateTime(this.attendance.check_in));
        this.check_out_time = this.formatDateTime(this.attendance.check_out && deserializeDateTime(this.attendance.check_out));
        this.kiosk_delay = setTimeout(() => {
            this.props.kioskReturn(true)
        }, this.props.employeeData.kiosk_delay)
        if (this.props.employeeData.display_overtime){
            this.overtimeToday = this.formatFloatTime(this.props.employeeData.overtime_today);
            this.totalOvertime = this.formatFloatTime(this.props.employeeData.total_overtime);
        }
        onWillDestroy(() => clearTimeout(this.kiosk_delay));
    }
}
