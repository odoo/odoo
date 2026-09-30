import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarWithRecurrenceCommonRenderer } from './calendar_with_recurrence_common_renderer';
import { CalendarWithRecurrenceYearRenderer } from './calendar_with_recurrence_year_renderer';

export class CalendarWithRecurrenceRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: CalendarWithRecurrenceCommonRenderer,
        week: CalendarWithRecurrenceCommonRenderer,
        month: CalendarWithRecurrenceCommonRenderer,
        year: CalendarWithRecurrenceYearRenderer,
    };
}
