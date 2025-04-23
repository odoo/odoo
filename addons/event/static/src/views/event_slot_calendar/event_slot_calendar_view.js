import { calendarView } from "@web/views/calendar/calendar_view";
import { EventSlotCalendarModel } from "@event/views/event_slot_calendar/event_slot_calendar_model";
import { EventSlotCalendarRenderer } from "@event/views/event_slot_calendar/event_slot_calendar_renderer";
import { registry } from "@web/core/registry";


export const EventSlotCalendarView = {
    ...calendarView,
    Model: EventSlotCalendarModel,
    Renderer: EventSlotCalendarRenderer,
};

registry.category("views").add("event_slot_calendar", EventSlotCalendarView);
