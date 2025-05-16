import { CalendarController } from "@web/views/calendar/calendar_controller";

import { TimesheetCalendarMyTimesheetsSidePanel } from "./timesheet_calendar_my_timesheets_side_panel/timesheet_calendar_my_timesheets_side_panel";

export class TimesheetCalendarMyTimesheetsController extends CalendarController {
    static components = {
        ...CalendarController.components,
        CalendarSidePanel: TimesheetCalendarMyTimesheetsSidePanel,
    };
}
