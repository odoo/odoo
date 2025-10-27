import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

export class EventSlotCalendarCommonRenderer extends CalendarCommonRenderer {
    // Display end time and hide title on the full calendar library event.
    static eventTemplate = "event.EventSlotCalendarCommonRenderer.event";

    /**
     * Add overlay on days outside of event time range.
     */
    getDayCellClassNames(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        const serverDatetimeFormat = 'yyyy-MM-dd HH:mm:ss';
        const rangeStartDate = this.props.model.data.event?.start
            ?.toFormat(serverDatetimeFormat, { numberingSystem: 'latn' })
            .split(" ")[0];
        const rangeEndDate = this.props.model.data.event?.end
            ?.toFormat(serverDatetimeFormat, { numberingSystem: 'latn' })
            .split(" ")[0];
        if (
            rangeStartDate &&
            rangeEndDate &&
            (date < rangeStartDate || date > rangeEndDate)
        ) {
            return ["o_calendar_disabled"];
        }
        return [];
    }

    /**
     * @override
     * Slots cannot be created over multiple days on mobile.
     * On desktop, using the multi create feature which doesn't consider this value.
     */
    isSelectionAllowed(event) {
        return false;
    }
}

export class EventSlotCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: EventSlotCalendarCommonRenderer,
        week: EventSlotCalendarCommonRenderer,
        month: EventSlotCalendarCommonRenderer,
        year: CalendarYearRenderer,
    };
}
