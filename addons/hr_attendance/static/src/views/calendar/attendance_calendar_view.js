import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { AttendanceControlPanel } from "@hr_attendance/components/attendance_dashboard/attendance_control_panel";
import { AttendanceCalendarController } from "./attendance_calendar_controller";
import { AttendanceCalendarRenderer } from "./attendance_calendar_renderer";
import { AttendanceCalendarModel } from "./attendance_calendar_model";

const AttendanceCalendarView = {
    ...calendarView,
    Model: AttendanceCalendarModel,
    Controller: AttendanceCalendarController,
    Renderer: AttendanceCalendarRenderer,
    ControlPanel: AttendanceControlPanel,
};

registry.category("views").add("attendance_calendar_view", AttendanceCalendarView);
