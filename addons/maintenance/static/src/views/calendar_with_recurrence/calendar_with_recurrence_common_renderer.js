/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarWithRecurrenceCommonPopover } from "./calendar_with_recurrence_common_popover";

export class CalendarWithRecurrenceCommonRenderer extends CalendarCommonRenderer { }

CalendarWithRecurrenceCommonRenderer.components = {
    ...CalendarCommonRenderer.components,
    Popover: CalendarWithRecurrenceCommonPopover,
};
