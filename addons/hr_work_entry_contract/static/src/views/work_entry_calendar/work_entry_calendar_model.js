import { CalendarModel } from "@web/views/calendar/calendar_model";
import { useWorkEntry } from "@hr_work_entry_contract/views/work_entry_hook";

const { DateTime } = luxon;

export class WorkEntryCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        const { generateWorkEntries } = useWorkEntry({ getRange: this.computeRange.bind(this) });
        this.generateWorkEntries = generateWorkEntries;
    }

    async updateData(data) {
        const { start } = this.computeRange();
        const shouldGenerateWorkEntries = start <= DateTime.now();
        if (shouldGenerateWorkEntries) {
            await this.generateWorkEntries();
        }
        await super.updateData(data);
    }
}
