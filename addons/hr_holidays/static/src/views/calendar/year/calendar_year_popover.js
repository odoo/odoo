import { Dialog } from "@web/core/dialog/dialog";

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { getFormattedDateSpan } from "@web/views/calendar/utils";
import { getLeaveLastMoment } from "../utils";

export class TimeOffCalendarYearPopover extends CalendarYearPopover {
    static components = { Dialog };
    static template = "web.CalendarYearPopover";
    static subTemplates = {
        ...CalendarYearPopover.subTemplates,
        body: "hr_holidays.MandatoryDayCalendarYearPopover.body",
        record: "hr_holidays.CalendarYearPopover.record",
    };

    /**
     * @override
     * Groups are named by the days their leaves cover, not by the bound that closes them.
     */
    groupRecords() {
        const recordGroups = {};
        for (const group of super.groupRecords()) {
            const end = getLeaveLastMoment(group.records[0]);
            const title = getFormattedDateSpan(group.start, end);
            const recordGroup = (recordGroups[title] ??= { ...group, title, end, records: [] });
            recordGroup.start = luxon.DateTime.min(recordGroup.start, group.start);
            recordGroup.end = luxon.DateTime.max(recordGroup.end, end);
            recordGroup.records.push(...group.records);
        }
        return Object.values(recordGroups);
    }
}
