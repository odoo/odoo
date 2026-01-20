/** @odoo-module **/
import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";
import { ResourceCalendarAttendanceCalendarRenderer } from "./resource_calendar_attendance_calendar_renderer";
import { ResourceCalendarAttendanceCalendarModel } from "./resource_calendar_attendance_calendar_model";
import { ResourceCalendarAttendanceCalendarController } from "./resource_calendar_attendance_calendar_controller";

export const ResourceCalendarAttendanceCalendarView = {
    ...calendarView,
    Controller: ResourceCalendarAttendanceCalendarController,
    Renderer: ResourceCalendarAttendanceCalendarRenderer,
    Model: ResourceCalendarAttendanceCalendarModel,
};

registry
    .category("views")
    .add("resource_calendar_attendance_calendar", ResourceCalendarAttendanceCalendarView);
