import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { MRPCalendarRenderer } from '@mrp/views/calendar/mrp_calendar_renderer';

export const MRPCalendarView = {
    ...calendarView,
    Renderer: MRPCalendarRenderer,
}
registry.category("views").add('mrp_calendar', MRPCalendarView);
