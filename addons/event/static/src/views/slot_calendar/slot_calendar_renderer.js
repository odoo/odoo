import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { SlotCalendarMixin } from "@event/views/slot_calendar/slot_calendar_mixin";


class SlotCalendarCommonRenderer extends SlotCalendarMixin(CalendarCommonRenderer) {
    /**
     * On slot click, triggers an event then caught by
     * the slot picker field and close the action dialog.
     */
    onClick(info) {
        this.env.bus.trigger('slot_selected', [
            luxon.DateTime.fromJSDate(info.event.start),
            luxon.DateTime.fromJSDate(info.event.end),
        ]);
        this.env.searchModel.dialog.closeAll();
    }
}

class SlotCalendarYearRenderer extends SlotCalendarMixin(CalendarYearRenderer) {}

export class SlotCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: SlotCalendarCommonRenderer,
        week: SlotCalendarCommonRenderer,
        month: SlotCalendarCommonRenderer,
        year: SlotCalendarYearRenderer,
    };
}
