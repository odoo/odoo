import { CalendarController } from "@web/views/calendar/calendar_controller";
import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";
import { SlotCalendarModel } from "@event/views/slot_calendar/slot_calendar_model";
import { SlotCalendarRenderer } from "@event/views/slot_calendar/slot_calendar_renderer";

const slotCalendarView = {
    ...calendarView,
    Controller: CalendarController,
    Model: SlotCalendarModel,
    Renderer: SlotCalendarRenderer,
};

registry.category("views").add("event_slot_calendar", slotCalendarView);
