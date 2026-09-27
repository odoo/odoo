import { registry } from "@web/core/registry";
import { TimeOffReportCalendarController } from "./time_off_report_calendar_controller";
import { timeOffCalendarHrLeaveView } from "./calendar_view";

export const timeOffReportCalendarView = {
    ...timeOffCalendarHrLeaveView,
    Controller: TimeOffReportCalendarController,
};
registry.category("views").add("time_off_report_calendar", timeOffReportCalendarView);
