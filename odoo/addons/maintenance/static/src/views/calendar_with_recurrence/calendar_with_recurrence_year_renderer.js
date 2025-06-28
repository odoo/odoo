/** @odoo-module **/

import { CalendarWithRecurrenceYearPopover } from "./calendar_with_recurrence_year_popover";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

export class CalendarWithRecurrenceYearRenderer extends CalendarYearRenderer { }

CalendarWithRecurrenceYearRenderer.components = {
    ...CalendarYearRenderer.components,
    Popover: CalendarWithRecurrenceYearPopover,
};
