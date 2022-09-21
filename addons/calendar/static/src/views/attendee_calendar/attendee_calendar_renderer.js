/** @odoo-module **/

import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
// import { useService } from "@web/core/utils/hooks";
import { AttendeeCalendarCommonRenderer } from "@calendar/views/attendee_calendar/common/attendee_calendar_common_renderer";

export class AttendeeCalendarRenderer extends CalendarRenderer {}
AttendeeCalendarRenderer.components = {
    ...CalendarRenderer.components,
    day: AttendeeCalendarCommonRenderer,
    week: AttendeeCalendarCommonRenderer,
    year: AttendeeCalendarCommonRenderer,
};
