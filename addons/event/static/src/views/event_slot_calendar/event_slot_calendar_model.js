import { CalendarModel } from "@web/views/calendar/calendar_model";
import { serializeDate } from "@web/core/l10n/dates";

export class EventSlotCalendarModel extends CalendarModel {

    /**
     * @override
     * Save slot date and hours from selected datetimes
     */
    buildRawRecord(partialRecord, options = {}) {
        const rawRecord = super.buildRawRecord(partialRecord, options)
        rawRecord["date"] = serializeDate(partialRecord.start);
        rawRecord["start_hour"] = partialRecord.start.hour + partialRecord.start.minute / 60;
        rawRecord["end_hour"] = partialRecord.end.hour + partialRecord.end.minute / 60;
        return rawRecord;
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
        return normalizedRecord;
    }

}
