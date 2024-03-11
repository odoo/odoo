/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class TimeOffCalendarYearPopover extends CalendarYearPopover {}
TimeOffCalendarYearPopover.components = { Dialog };
TimeOffCalendarYearPopover.template = "web.CalendarYearPopover";
TimeOffCalendarYearPopover.subTemplates = {
    ...CalendarYearPopover.subTemplates,
    body: "hr_holidays.StressDayCalendarYearPopover.body",
};
