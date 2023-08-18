/** @odoo-module */

import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { CalendarModel } from '@web/views/calendar/calendar_model';

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
            if (rawRecord.recurring_maintenance && !rawRecord.done && !rawRecord.archive) {
                let { start, end } = data.range;
                if (rawRecord.repeat_type == 'until') {
                    end = luxon.DateTime.min(end, deserializeDateTime(rawRecord.repeat_until)).endOf('day');
                }
                let date = deserializeDateTime(rawRecord.schedule_date);
                date = this._getNextDate(date, rawRecord.repeat_unit + 's', rawRecord.repeat_interval);
                let counter = 1;
                while (date <= end) {
                    if (date > start) {
                        const rawRecordCopy = { ...rawRecord };
                        rawRecordCopy.display_name = rawRecord.display_name + " (+" + counter + ")";
                        rawRecordCopy.schedule_date = serializeDateTime(date);
                        records[recordsCounter] = {
                            ...this.normalizeRecord(rawRecordCopy),
                            id: recordsCounter,
                        };
                        recordsCounter++;
                    }
                    date = this._getNextDate(date, rawRecord.repeat_unit + 's', rawRecord.repeat_interval);
                    counter++;
                }
            }
        }
        return records;
    }
    _getNextDate(date, unit, interval) {
        return date.plus({ [unit]: interval });
    }
}
