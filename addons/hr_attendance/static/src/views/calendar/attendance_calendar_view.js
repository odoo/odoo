import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { AttendanceCalendarController } from "./attendance_calendar_controller";

const AttendanceCalendarView = {
    ...calendarView,
    Controller: AttendanceCalendarController,
};

registry.category("views").add("attendance_calendar_view", AttendanceCalendarView);
