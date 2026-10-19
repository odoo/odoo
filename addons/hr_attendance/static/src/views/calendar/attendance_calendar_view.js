import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { AttendanceCalendarController } from "./attendance_calendar_controller";
import { AttendanceCalendarRenderer } from "./attendance_calendar_renderer";

const AttendanceCalendarView = {
    ...calendarView,
    Controller: AttendanceCalendarController,
    Renderer: AttendanceCalendarRenderer,
};

registry.category("views").add("attendance_calendar_view", AttendanceCalendarView);
