import { Component, useState, onWillUnmount } from "@odoo/owl";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

const { DateTime } = luxon;
export class CardLayout extends Component {
    static template = "hr_attendance.CardLayout";
    static components = { AttendanceVideoStream };
    static props = {
        slots: Object,
        fromTrialMode: { type: Boolean, optional: true },
        companyImageUrl: { type: String },
        kioskReturn: { type: Function },
        activeDisplay: { type: String },
        captureCheckInPicture: { type: Boolean },
        exposeCamera: { type: Function, optional: true },
    };
    static defaultProps = {
        kioskModeClasses: "",
    };

    setup() {
        this.state = useState(this.getDateTime());
        this.timeInterval = setInterval(() => {
            Object.assign(this.state, this.getDateTime());
        }, 1000);
        onWillUnmount(() => {
            clearInterval(this.timeInterval);
        });
    }

    getDateTime() {
        const now = DateTime.now();
        return {
            dayOfWeek: now.toFormat("cccc"),
            date: now.toLocaleString({
                ...DateTime.DATE_FULL,
                weekday: undefined,
            }),
            time: now.toLocaleString(DateTime.TIME_SIMPLE),
        };
    }
}
