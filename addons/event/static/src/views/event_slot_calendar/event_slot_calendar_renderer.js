import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

export class EventSlotCalendarCommonRenderer extends CalendarCommonRenderer {
    // Display end time and hide title on the full calendar library event.
    static eventTemplate = "event.EventSlotCalendarCommonRenderer.event";
    // Prevent square selection over disabled cells on desktop.
    static cellIsSelectable = (cell) => !cell.classList.contains("o_calendar_disabled");

    setup() {
        super.setup(...arguments);
        this.rangeStartDate = this.props.model.meta.context.event_calendar_range_start_date;
        this.rangeEndDate = this.props.model.meta.context.event_calendar_range_end_date;
    }

    /**
     * Add overlay to disable days outside of event time range.
     */
    getDayCellClassNames(info) {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        if (
            this.rangeStartDate &&
            this.rangeEndDate &&
            (date < this.rangeStartDate || date > this.rangeEndDate)
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

    /**
     * @override
     * Prevent click on disabled dates in mobile.
    */
    onDateClick(info) {
        if (info.dayEl.classList.contains("o_calendar_disabled")) {
            return;
        }
        return super.onDateClick(info);
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
