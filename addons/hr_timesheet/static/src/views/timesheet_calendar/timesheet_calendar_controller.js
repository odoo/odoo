import { TimesheetCalendarMyTimesheetsController } from "../timesheet_calendar_my_timesheets/timesheet_calendar_my_timesheets_controller";

import { TimesheetCalendarSidePanel } from "./timesheet_calendar_side_panel/timesheet_calendar_side_panel";

export class TimesheetCalendarController extends TimesheetCalendarMyTimesheetsController {
    static components = {
        ...TimesheetCalendarMyTimesheetsController.components,
        CalendarSidePanel: TimesheetCalendarSidePanel,
    };
}
