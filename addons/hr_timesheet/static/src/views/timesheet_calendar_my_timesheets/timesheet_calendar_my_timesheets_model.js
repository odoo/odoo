import { CalendarModel } from "@web/views/calendar/calendar_model";

export class TimesheetCalendarMyTimesheetsModel extends CalendarModel {
    multiCreateRecords(dates) {
        this.meta.context = this.meta.context || {};
        this.meta.context.timesheet_calendar = true;
        super.multiCreateRecords(dates);
    }
}
