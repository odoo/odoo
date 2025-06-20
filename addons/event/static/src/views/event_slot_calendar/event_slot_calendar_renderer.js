import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

import { useEffect } from "@odoo/owl";

export class EventSlotCalendarCommonRenderer extends CalendarCommonRenderer {
    // Display end time and hide title on the full calendar library event.
    static eventTemplate = "event.EventSlotCalendarCommonRenderer.event";

    setup() {
        super.setup(...arguments);
        this.rangeStartDate = this.props.model.meta.context.event_start_date.split(' ')[0];
        this.rangeEndDate = this.props.model.meta.context.event_end_date.split(' ')[0];
        useEffect(
            (fcEls) => {
                // Add overlay to disable days outside of event time range.
                for (const fcEl of fcEls) {
                    fcEl.querySelectorAll(".fc-day:not(.fc-col-header-cell)").forEach((dayEl) => {
                        if (dayEl.dataset.date < this.rangeStartDate || dayEl.dataset.date > this.rangeEndDate) {
                            // 'pe-none' to disable month view multi records creation
                            // 'o_event_day_disabled' class to disable single record creation
                            dayEl.classList.add("bg-secondary", "bg-opacity-25", "pe-none", "o_event_disabled_day");
                        }
                    });
                }
            },
            () => [[this.fc.el]],
        );
    }

    /**
     * @override
     * Slots cannot be created over multiple days.
     */
    isSelectionAllowed(event) {
        return false;
    }

    /**
     * @override
     * Prevent click on disabled dates.
    */
    onDateClick(info) {
        if (info.dayEl.classList.contains("o_event_disabled_day")) {
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
