import { calendarView } from "@web/views/calendar/calendar_view";
import { WorkEntryCalendarRenderer } from "@hr_work_entry/views/work_entry_calendar/work_entry_calendar_renderer";
import { WorkEntryCalendarModel } from "@hr_work_entry/views/work_entry_calendar/work_entry_calendar_model";
import { registry } from "@web/core/registry";
import { WorkEntryCalendarController } from "@hr_work_entry/views/work_entry_calendar/work_entry_calendar_controller";

export const WorkEntryCalendarView = {
    ...calendarView,
    Controller: WorkEntryCalendarController,
    Renderer: WorkEntryCalendarRenderer,
    Model: WorkEntryCalendarModel,
    buttonTemplate: "hr_work_entry.calendar.controlButtons",
};

registry.category("views").add("work_entries_calendar", WorkEntryCalendarView);
