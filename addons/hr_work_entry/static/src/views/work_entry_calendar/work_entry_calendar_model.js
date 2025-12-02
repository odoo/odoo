import { serializeDate } from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { CalendarModel } from "@web/views/calendar/calendar_model";

const { DateTime } = luxon;

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
            [this.meta.context.default_employee_id],
            serializeDate(start),
            serializeDate(end),
        ]);
        await Promise.all([
            super.updateData(...arguments),
            this._fetchUserFavoritesWorkEntries(),
        ]);
    }

    async _fetchUserFavoritesWorkEntries() {
        const userFavoritesWorkEntriesIds = await this.orm.formattedReadGroup(
            "hr.work.entry",
            [
                ["create_uid", "=", user.userId],
                ["create_date", ">", serializeDate(DateTime.local().minus({ months: 3 }))],
            ],
            ["work_entry_type_id", "create_date:day"],
            [],
            {
                order: "create_date:day desc",
                limit: 6,
            }
        );
        if (userFavoritesWorkEntriesIds.length) {
            this.userFavoritesWorkEntries = await this.orm.read(
                "hr.work.entry.type",
                userFavoritesWorkEntriesIds.map((r) => r.work_entry_type_id?.[0]).filter(Boolean),
                ["display_name", "display_code", "color"]
            );
            this.userFavoritesWorkEntries = this.userFavoritesWorkEntries.sort((a, b) =>
                a.display_code
                    ? a.display_code.localeCompare(b.display_code)
                    : a.display_name.localeCompare(b.display_name)
            );
        } else {
            this.userFavoritesWorkEntries = [];
        }
    }

    async multiReplaceRecords(values, dates, records) {
        if (!dates.length) {
            return;
        }
        const new_records = [];
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
            employee_id: this.meta.context.default_employee_id,
        }));
        await this.orm.call("hr.work.entry.regeneration.wizard", "regenerate_work_entries", [
            [],
            cellsFormattedData,
            recordIds,
        ]);
        return this.load();
    }
}
