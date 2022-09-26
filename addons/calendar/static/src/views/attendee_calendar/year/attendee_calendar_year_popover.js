/** @odoo-module **/

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class AttendeeCalendarYearPopover extends CalendarYearPopover {}
AttendeeCalendarYearPopover.subTemplates = {
    ...CalendarYearPopover.subTemplates,
    body: "calendar.AttendeeCalendarYearPopover.body",
};
