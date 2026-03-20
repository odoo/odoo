import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { MRPCalendarCommonRenderer } from '@mrp/views/calendar/common/mrp_calendar_common_renderer';

export class MRPCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: MRPCalendarCommonRenderer,
        week: MRPCalendarCommonRenderer,
    };
}
