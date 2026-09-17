/** @odoo-module native */
import {
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { CalendarModel } from "@web/views/calendar";

export class CalendarWithRecurrenceModel extends CalendarModel {
    async loadRecords(data) {
        const rawRecords = await this.fetchRecords(data);
        const planned = rawRecords.filter(
            (rawRecord) =>
                rawRecord.plan_id &&
                ["draft", "confirmed", "in_progress"].includes(rawRecord.state),
        );
        const occurrencesByOrder = planned.length
            ? await this.orm.call(this.meta.resModel, "get_plan_occurrences", [
                  planned.map((rawRecord) => rawRecord.id),
                  serializeDateTime(data.range.start),
                  serializeDateTime(data.range.end),
              ])
            : {};
        const records = {};
        let recordsCounter = 1;
        for (const rawRecord of rawRecords) {
            records[recordsCounter] = {
                ...this.normalizeRecord(rawRecord),
                id: recordsCounter,
            };
            recordsCounter++;
            const duration = rawRecord.duration || 1;
            const occurrences = occurrencesByOrder[rawRecord.id] || [];
            for (const [index, occurrence] of occurrences.entries()) {
                const date = deserializeDateTime(occurrence);
                records[recordsCounter] = {
                    ...this.normalizeRecord({
                        ...rawRecord,
                        display_name: `${rawRecord.display_name} (+${index + 1})`,
                        date_scheduled_start: occurrence,
                        date_scheduled_end: serializeDateTime(
                            date.plus({ hours: duration }),
                        ),
                    }),
                    id: recordsCounter,
                    isRecurrent: true,
                };
                recordsCounter++;
            }
        }
        return records;
    }
    computeRangeDomain(data) {
        // An order of a plan shows the plan's occurrences long after its own end, so
        // it stays in range while the plan can still repeat into it.
        const { date_start, date_stop } = this.meta.fieldMapping;
        const { start, end } = data.range;
        return [
            [date_start, "<=", serializeDateTime(end)],
            "|",
            "|",
            [date_stop, ">=", serializeDateTime(start)],
            [date_stop, "=", false],
            "&",
            "&",
            ["state", "in", ["draft", "confirmed", "in_progress"]],
            ["plan_id.active", "=", true],
            "|",
            ["plan_id.repeat_type", "!=", "until"],
            ["plan_id.repeat_until", ">=", serializeDate(start)],
        ];
    }
    normalizeRecord(rawRecord) {
        // Override to set end = start + 1h if date_scheduled_end is False.
        const record = super.normalizeRecord(rawRecord);
        const { duration, start, end } = record;
        if (!end.isValid && duration) {
            record.end = start.plus({ hours: duration });
            record.isTimeHidden = false;
        }
        return record;
    }
}
