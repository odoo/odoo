import { CalendarModel } from "@web/views/calendar/calendar_model";

export class TimesheetCalendarMyTimesheetsModel extends CalendarModel {
    /**
     * @override
     */
    async multiCreateRecords(multiCreateData, dates) {
        this.meta.context = this.meta.context || {};
        this.meta.context.timesheet_calendar = true;
        return await super.multiCreateRecords(multiCreateData, dates);
    }
}
