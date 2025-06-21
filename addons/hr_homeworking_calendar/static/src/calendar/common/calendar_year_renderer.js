/** @odoo-module **/

import { AttendeeCalendarYearRenderer } from "@calendar/views/attendee_calendar/year/attendee_calendar_year_renderer";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarYearRenderer, {
    props: {
        ...AttendeeCalendarYearRenderer.props,
        openWorkLocationWizard: { type: Function, optional: true },
    }
});
