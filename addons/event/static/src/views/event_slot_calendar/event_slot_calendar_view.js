import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { calendarView } from "@web/views/calendar/calendar_view";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { registry } from "@web/core/registry";
import { serializeDate } from "@web/core/l10n/dates";

export class EventSlotCalendarModel extends CalendarModel {

    /**
     * @override
     * Save slot date using selected date
     */
    buildRawRecord(partialRecord, options = {}) {
        const rawRecord = super.buildRawRecord(partialRecord, options)
        rawRecord["date"] = serializeDate(partialRecord.start);
        return rawRecord;
    }

    /**
     * @override
     * Instead of the local tz, express the times in the related event or event type tz or fallback on utc.
     */
    normalizeRecord(rawRecord) {
        const normalizedRecord = super.normalizeRecord(rawRecord);
        const tz = rawRecord.date_tz || 'utc';
        normalizedRecord.start = normalizedRecord.start.setZone(tz);
        normalizedRecord.end = normalizedRecord.end.setZone(tz);
        return normalizedRecord;
    }

}

export class EventSlotCalendarCommonRenderer extends CalendarCommonRenderer {
    // Display end time and hide title on the fc event
    static eventTemplate = "event.EventSlotCalendarCommonRenderer.event";
}

export class EventSlotCalendarYearRenderer extends CalendarYearRenderer {
    // The multi create behavior is only meant for the common renderer (day, week and month views).
    // To keep things consistent between the different views, remove the records creation from the year renderer.

    /**
     * @override
     * Disable record creation on date click
     */
    onDateClick(info) {
        return;
    }

    /**
     * @override
     * Disable records creation on selection
     */
    async onSelect(info) {
        this.popover.close();
        this.unselect();
    }
}

export class EventSlotCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        day: EventSlotCalendarCommonRenderer,
        week: EventSlotCalendarCommonRenderer,
        month: EventSlotCalendarCommonRenderer,
        year: EventSlotCalendarYearRenderer,
    };
}

export const EventSlotCalendarView = {
    ...calendarView,
    Model: EventSlotCalendarModel,
    Renderer: EventSlotCalendarRenderer,
};

registry.category("views").add("event_slot_calendar", EventSlotCalendarView);
