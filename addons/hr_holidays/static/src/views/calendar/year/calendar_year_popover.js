import { Dialog } from "@web/ui/dialog/dialog";

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class TimeOffCalendarYearPopover extends CalendarYearPopover {
    static components = { Dialog };
    static template = "web.CalendarYearPopover";
    static subTemplates = {
        ...CalendarYearPopover.subTemplates,
        body: "hr_holidays.MandatoryDayCalendarYearPopover.body",
    };
}
