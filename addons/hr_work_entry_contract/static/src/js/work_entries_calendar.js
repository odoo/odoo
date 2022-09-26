/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CalendarController } from '@web/views/calendar/calendar_controller';
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { calendarView } from "@web/views/calendar/calendar_view";
import { useWorkEntry } from "@hr_work_entry_contract/js/work_entries_controller_mixin_owl";

const { DateTime } = luxon;
export class WorkEntryCalendarController extends CalendarController {
    setup() {
        super.setup(...arguments);
        const { onRegenerateWorkEntries } = useWorkEntry();
        this.onRegenerateWorkEntries = onRegenerateWorkEntries;
    }
}

export class WorkEntryCalendarModel extends CalendarModel {
    setup() {
        super.setup(...arguments);
        const { generateWorkEntries } = useWorkEntry();
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
            active: true
        };
    }

    async updateData(data) {
        const { start, end } = this.computeRange(data);
        const shouldGenerateWorkEntries = start <= DateTime.now().plus({months: 10});
        if (shouldGenerateWorkEntries) {
            await this.generateWorkEntries(start, end);
        }
        await super.updateData(data);
    }
}

export const WorkEntryCalendarView = {
    ...calendarView,
    Controller: WorkEntryCalendarController,
    Model: WorkEntryCalendarModel,
    buttonTemplate: "hr_work_entry_contract.calendar.controlButtons"
}

registry.category("views").add("work_entries_calendar", WorkEntryCalendarView);
