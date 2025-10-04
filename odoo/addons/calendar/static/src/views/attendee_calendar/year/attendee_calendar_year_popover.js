/** @odoo-module **/

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class AttendeeCalendarYearPopover extends CalendarYearPopover {
    getRecordClass(record) {
        const classes = [super.getRecordClass(record)];
        if (record.isAlone) {
            classes.push("o_attendee_status_alone");
        } else {
            classes.push(`o_attendee_status_${record.attendeeStatus}`);
        }
        return classes.join(" ");
    }
}
AttendeeCalendarYearPopover.subTemplates = {
    ...CalendarYearPopover.subTemplates,
    body: "calendar.AttendeeCalendarYearPopover.body",
};
