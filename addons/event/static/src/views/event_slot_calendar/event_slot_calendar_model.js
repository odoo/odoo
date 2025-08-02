import { CalendarModel } from "@web/views/calendar/calendar_model";
import { serializeDate } from "@web/core/l10n/dates";
import { Time } from "@web/core/l10n/time";

export class EventSlotCalendarModel extends CalendarModel {

    /**
     * @override
     * Save slot date and hours from selected datetimes
     */
    buildRawRecord(partialRecord, options = {}) {
        const rawRecord = super.buildRawRecord(partialRecord, options);
        rawRecord["date"] = serializeDate(partialRecord.start);
        rawRecord["start_hour"] = partialRecord.start.hour + partialRecord.start.minute / 60;
        if (partialRecord.end) {
            rawRecord["end_hour"] = partialRecord.end.hour + partialRecord.end.minute / 60;
        }
        return rawRecord;
    }

    /**
     * @override
     * Save selected date in context defaults for quick create form.
     */
    makeContextDefaults(rawRecord) {
        const context = super.makeContextDefaults(rawRecord);
        context["default_date"] = rawRecord["date"];
        return context;
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

    /**
     * @override
     * Preserve slot duration when updating the start time by automatically adjusting the end time.
     */
    setMultiCreateTimeRange(timeRange) {
        if (timeRange.start) {
            const previousEndValues = this.getItemFromStorage("multiCreateTimeEnd", { hour: 13, minute: 0 });
            const newStart = new Time(timeRange.start).toDateTime();
            const previousStart = new Time(this.getItemFromStorage("multiCreateTimeStart", { hour: 12, minute: 0 })).toDateTime();
            const previousEnd = new Time(previousEndValues).toDateTime();
            const previousDelta = previousEnd.diff(previousStart, ['hours', 'minutes', 'seconds']).values;
            const newEnd = newStart.plus({hour: previousDelta.hours, minute: previousDelta.minutes, second: previousDelta.seconds});
            timeRange.end = new Time({
                ...previousEndValues,
                hour: newEnd.hour,
                minute: newEnd.minute,
                second: newEnd.second,
            });
        }
        super.setMultiCreateTimeRange(timeRange);
        this.notify();
    }

}
