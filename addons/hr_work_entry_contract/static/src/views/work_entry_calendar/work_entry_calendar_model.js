/** @odoo-module **/

import { CalendarModel } from "@web/views/calendar/calendar_model";
import { useWorkEntry } from "@hr_work_entry_contract/views/work_entry_hook";

const { DateTime } = luxon;

export class WorkEntryCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        const { generateWorkEntries } = useWorkEntry({ getRange: this.computeRange.bind(this) });
        this.generateWorkEntries = generateWorkEntries;
    }

    computeRange() {
        const { scale, date } = this.meta;
        const start = date.startOf(scale);
        const end = date.endOf(scale);
        return { start, end };
    }

    makeFilterAll() {
        return {
            ...super.makeFilterAll(...arguments),
            label: this.env._t("Everybody's work entries"),
            active: true,
        };
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
