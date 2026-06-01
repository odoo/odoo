import { Component, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

export class KioskConfirmation extends Component {
    static template = "hr_attendance.KioskConfirmation";
    static components = {
        AttendanceVideoStream,
    };
    static props = {
        employeeData: { type: Object },
        kioskConfirm: { type: Function },
        backToManualSelection: { type: Function },
        captureCheckInImage: { type: Boolean },
        exposeCameraCapture: { type: Function },
    };

    setup() {
        this.formatFloatTime = registry.category("formatters").get("float_time");
        this.state = proxy({
            streamAvailable: null,
        });

        this.employeeName = this.props.employeeData.employee_name;
        this.employeeAvatar = this.props.employeeData.employee_avatar;
        this.hoursToday = this.formatFloatTime(this.props.employeeData.hours_today);
        this.attendance = this.props.employeeData.attendance;
    }

    get isCheckedIn() {
        return this.props.employeeData.attendance_state === "checked_in";
    }

    get showVideoStream() {
        return (
            this.props.captureCheckInImage &&
            !this.isCheckedIn &&
            this.state.streamAvailable !== false
        );
    }

    setStreamAvailable(isAvailable) {
        this.state.streamAvailable = isAvailable;
    }
}
