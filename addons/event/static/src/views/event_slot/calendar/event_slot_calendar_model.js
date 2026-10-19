import { CalendarModel } from "@web/views/calendar/calendar_model";
import { deserializeDateTime, serializeDate } from "@web/core/l10n/dates";

/**
 * Slots are created differently depending on the screen size.
 * Desktop: "New" button or multi create feature.
 * Mobile: "New" button or quick create dialog.
 */
export class EventSlotCalendarModel extends CalendarModel {

    setup(params, services) {
        super.setup(...arguments);
        this.orm = services.orm;
    }

    /**
     * @override
     * Saves the event's time range and timezone to the model data.
     * The time range is converted to the event's timezone to correctly represent them on the calendar.
     * Fetches from db instead of using context to always ensure up-to-date values.
     */
    async load(params = {}) {
        const eventId = params.context?.default_event_id;
        const eventVals = eventId && this.orm.read(
            "event.event",
            [eventId],
            ["date_begin", "date_end", "date_tz"],
        );
        const res = await super.load(...arguments);
        if (eventId) {
            // Removing the timezone info to prevent any implicit
            // time conversion when comparing with other datetimes.
            const [{ date_begin: start, date_end: end, date_tz: tz }] = await eventVals;
            this.data.event = {
                id: eventId,
                start: deserializeDateTime(start, {tz: tz}).setZone(undefined, { keepLocalTime: true }),
                end: deserializeDateTime(end, {tz: tz}).setZone(undefined, { keepLocalTime: true }),
                tz,
            };
        }
        return res;
    }

    /**
     * @override
     * Set slot date and hours from selected datetimes.
     */
    buildRawRecord(partialRecord, options = {}) {
        const rawRecord = super.buildRawRecord(partialRecord, options);
        rawRecord["date"] = serializeDate(partialRecord.start);
        rawRecord["start_hour"] = partialRecord.start.hour + partialRecord.start.minute / 60;
        // There could be no 'end' when opening the mobile quick create dialog.
        if (partialRecord.end) {
            rawRecord["end_hour"] = partialRecord.end.hour + partialRecord.end.minute / 60;
        }
        return rawRecord;
    }

    /**
     * @override
     * Save selected date in context defaults for mobile quick create form dialog.
     *
     * Only needed for mobile quick create as the desktop multi create feature
     * is directly saving the raw records with the 'date' returned from 'buildRawRecord'.
     */
    makeContextDefaults(rawRecord) {
        const context = super.makeContextDefaults(rawRecord);
        context["default_date"] = rawRecord["date"];
        return context;
    }

    /**
     * @override
     * Instead of the local tz, express the times in the related event tz or fallback on utc.
     *
     * After conversion to event tz, changing the 'zone' param back to local without changing
     * the already converted datetimes. This is to make sure the calendar renders records correctly
     * as it always expects datetimes expressed in the 'local' tz.
     */
    normalizeRecord(rawRecord) {
        const normalizedRecord = super.normalizeRecord(rawRecord);
        const tz = rawRecord.date_tz || 'utc';
        normalizedRecord.start = normalizedRecord.start.setZone(tz).setZone('local', {keepLocalTime: true});
        normalizedRecord.end = normalizedRecord.end.setZone(tz).setZone('local', {keepLocalTime: true});
        // Always display the slot time
        normalizedRecord.isTimeHidden = false;
        return normalizedRecord;
    }

}
