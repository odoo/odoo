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
     * A group ends on the day its leaves cover last, not on the bound that closes them, so
     * two groups the parent tells apart by that bound alone name the same days and merge.
     */
    groupRecords() {
        const recordGroups = {};
        for (const group of super.groupRecords()) {
            const end = getLeaveLastMoment(group.records[0]);
            const title = getFormattedDateSpan(group.start, end);
            const recordGroup = (recordGroups[title] ??= { ...group, title, end, records: [] });
            recordGroup.records.push(...group.records);
        }
        return Object.values(recordGroups);
    }
}
