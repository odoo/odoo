/** @odoo-module **/

import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class CalendarWithRecurrenceYearPopover extends CalendarYearPopover {
    onRecordClick(record) {
        record.id = record.rawRecord.id;
        super.onRecordClick(record);
    }
}
