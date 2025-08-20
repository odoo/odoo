import { CalendarModel } from "@web/views/calendar/calendar_model";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";

export class WorkEntryCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    }

    /**
     * @override
     */
    async updateData(data) {
        const { start, end } = this.computeRange();
        await this.orm.call("hr.employee", "generate_work_entries", [
            [this.meta.context.active_id],
            serializeDate(start),
            serializeDate(end),
        ]);
        await super.updateData(...arguments);
    }

    async multiReplaceRecords(multiCreateData, dates, records) {
        if (!dates.length) {
            return;
        }
        const new_records = [];
        const values = await multiCreateData.record.getChanges();

        for (const date of dates) {
            const rawRecord = this.buildRawRecord({ start: date });
            new_records.push({
                ...rawRecord,
                ...values,
            });
        }
        const created = await this.orm.create(this.meta.resModel, new_records, {
            context: this.meta.context,
        });
        if (records.length && created) {
            await this.orm.unlink(this.meta.resModel, records);
        }
        return this.load();
    }

    async resetWorkEntries(dates, recordIds) {
        const cellsFormattedData = dates.map((date) => ({
            date,
            employee_id: this.meta.context.active_id,
        }));
        await this.orm.call("hr.work.entry.regeneration.wizard", "regenerate_work_entries", [
            [],
            [...cellsFormattedData],
            recordIds,
        ]);
        return this.load();
    }
}
