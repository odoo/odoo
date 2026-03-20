import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";

export const attendeeCalendarView = {
    ...calendarView,
    Controller: AttendeeCalendarController,
    Model: AttendeeCalendarModel,
    Renderer: AttendeeCalendarRenderer,
};

registry.category("views").add("attendee_calendar", attendeeCalendarView);
