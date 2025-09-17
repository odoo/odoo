import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { AttendeeCalendarModel } from "@calendar/views/attendee_calendar/attendee_calendar_model";
import { AttendeeCalendarRenderer } from "@calendar/views/attendee_calendar/attendee_calendar_renderer";
import { CalendarSyncButtons } from "@calendar/views/widgets/calendar_sync_buttons/calendar_sync_buttons";

export const attendeeCalendarView = {
    ...calendarView,
    Controller: AttendeeCalendarController,
    Model: AttendeeCalendarModel,
    Renderer: AttendeeCalendarRenderer,
};

attendeeCalendarView.components = {
    ...attendeeCalendarView.components,
    CalendarSyncButtons,
}

registry.category("views").add("attendee_calendar", attendeeCalendarView);
