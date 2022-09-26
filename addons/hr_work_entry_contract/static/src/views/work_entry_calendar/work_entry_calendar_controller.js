/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CalendarController } from '@web/views/calendar/calendar_controller';
import { WorkEntryCalendarModel } from "@hr_work_entry_contract/views/work_entry_calendar/work_entry_calendar_model";
import { calendarView } from "@web/views/calendar/calendar_view";
import { useWorkEntry } from "@hr_work_entry_contract/views/work_entry_hook";

export class WorkEntryCalendarController extends CalendarController {
    setup() {
        super.setup(...arguments);
        const { onRegenerateWorkEntries } = useWorkEntry({
            getEmployeeIds: this.getEmployeeIds.bind(this),
            getRange: this.model.computeRange.bind(this.model),
        });
        this.onRegenerateWorkEntries = onRegenerateWorkEntries;
    }

    getEmployeeIds() {
        return [...new Set(Object.values(this.model.records).map(rec => rec.rawRecord.employee_id[0]))];
    }
}

export const WorkEntryCalendarView = {
    ...calendarView,
    Controller: WorkEntryCalendarController,
    Model: WorkEntryCalendarModel,
    buttonTemplate: "hr_work_entry_contract.calendar.controlButtons",
}

registry.category("views").add("work_entries_calendar", WorkEntryCalendarView);
