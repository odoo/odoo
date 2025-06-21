import { registry } from "@web/core/registry";

import { calendarView } from "@web/views/calendar/calendar_view";

import { TimesheetCalendarMyTimesheetsController } from "./timesheet_calendar_my_timesheets_controller";
import { TimesheetCalendarMyTimesheetsModel } from "./timesheet_calendar_my_timesheets_model";

export const timesheetCalendarMyTimesheetsView = {
    ...calendarView,
    Controller: TimesheetCalendarMyTimesheetsController,
    Model: TimesheetCalendarMyTimesheetsModel,
};

registry
    .category("views")
    .add("timesheet_calendar_my_timesheets", timesheetCalendarMyTimesheetsView);
