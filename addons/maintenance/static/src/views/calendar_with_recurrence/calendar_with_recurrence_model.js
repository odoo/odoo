/** @odoo-module native */
import { luxon } from "@web/core/l10n/luxon";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { CalendarModel } from "@web/views/calendar";

export class CalendarWithRecurrenceModel extends CalendarModel {
    async loadRecords(data) {
        const rawRecords = await this.fetchRecords(data);
        const records = {};
        let recordsCounter = 1;
        for (const rawRecord of rawRecords) {
            records[recordsCounter] = {
                ...this.normalizeRecord(rawRecord),
                id: recordsCounter,
            };
            recordsCounter++;
            if (
                rawRecord.recurring_maintenance &&
                !rawRecord.done &&
                !rawRecord.archive
            ) {
                let { start, end } = data.range;
                if (rawRecord.repeat_type == "until") {
                    end = luxon.DateTime.min(
                        end,
                        deserializeDate(rawRecord.repeat_until).endOf("day"),
                    );
                }
                const duration = rawRecord.duration || 1;
                const [unit, interval] = [
                    rawRecord.repeat_unit + "s",
                    rawRecord.repeat_interval,
                ];
                const scheduleDate = deserializeDateTime(rawRecord.schedule_date);
                const origin = rawRecord.date_recurrence_origin
                    ? deserializeDateTime(rawRecord.date_recurrence_origin)
                    : scheduleDate;
                let step = 1;
                let date = this._getOccurrenceDate(origin, unit, interval, step);
                while (date <= scheduleDate) {
                    date = this._getOccurrenceDate(origin, unit, interval, ++step);
                }
                let counter = 1;
                while (date <= end) {
                    if (date > start) {
                        const endDate = date.plus({ hours: duration });
                        const rawRecordCopy = { ...rawRecord };
                        rawRecordCopy.display_name =
                            rawRecord.display_name + " (+" + counter + ")";
                        rawRecordCopy.schedule_date = serializeDateTime(date);
                        rawRecordCopy.schedule_end = serializeDateTime(endDate);
                        records[recordsCounter] = {
                            ...this.normalizeRecord(rawRecordCopy),
                            id: recordsCounter,
                            isRecurrent: true,
                        };
                        recordsCounter++;
                    }
                    date = this._getOccurrenceDate(origin, unit, interval, ++step);
                    counter++;
                }
            }
        }
        return records;
    }
    _getOccurrenceDate(origin, unit, interval, step) {
        return origin.plus({ [unit]: interval * step });
    }
    computeRangeDomain(data) {
        // A recurring request shows occurrences long after its own end, so it stays in
        // range while its rule can still repeat into it.
        const { date_start, date_stop } = this.meta.fieldMapping;
        const { start, end } = data.range;
        return [
            [date_start, "<=", serializeDateTime(end)],
            "|",
            "|",
            [date_stop, ">=", serializeDateTime(start)],
            [date_stop, "=", false],
            "&",
            ["recurring_maintenance", "=", true],
            "|",
            ["repeat_type", "!=", "until"],
            ["repeat_until", ">=", serializeDate(start)],
        ];
    }
    normalizeRecord(rawRecord) {
        // Override to set end = start + 1h if schedule_end is False.
        const record = super.normalizeRecord(rawRecord);
        const { duration, start, end } = record;
        if (!end.isValid && duration) {
            record.end = start.plus({ hours: duration });
            record.isTimeHidden = false;
        }
        return record;
    }
}
