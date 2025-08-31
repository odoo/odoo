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
        const quickreplace = (values.duration < 0);
        const newly_generated_entries = [];
        for (const date of dates) {
            const rawRecord = this.buildRawRecord({ start: date });
            if (quickreplace) {
                const selected_date_records = records.filter((r) => r.date === rawRecord.date);
                const existing_duration = selected_date_records.reduce((acc, r) => acc + r.duration, 0);
                if (existing_duration > 0)
                    values.duration = existing_duration;
                else {
                    const generated_work_entry = await this.orm.call(
                        "hr.employee",
                        "generate_work_entries",
                        [values.employee_id, date, date, true]
                    );
                    if (generated_work_entry.length > 0)
                        newly_generated_entries.push(generated_work_entry[0]);
                    continue
                }
            }
            new_records.push({
                ...rawRecord,
                ...values,
            });
        }
        await this.orm.write("hr.work.entry", newly_generated_entries, {
            work_entry_type_id: values.work_entry_type_id
        });
        const created = await this.orm.create(this.meta.resModel, new_records, {
            context: this.meta.context,
        });
        if (records.length && created) {
            await this.orm.unlink(this.meta.resModel, records.map((r) => r.id));
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
