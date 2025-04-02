import { CalendarModel } from "@web/views/calendar/calendar_model";
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
     * Instead of the local tz, express the times in the related event tz or fallback on utc.
     */
    normalizeRecord(rawRecord) {
        const normalizedRecord = super.normalizeRecord(rawRecord);
        const tz = rawRecord.date_tz || 'utc';
        normalizedRecord.start = normalizedRecord.start.setZone(tz);
        normalizedRecord.end = normalizedRecord.end.setZone(tz);
        return normalizedRecord;
    }

}
