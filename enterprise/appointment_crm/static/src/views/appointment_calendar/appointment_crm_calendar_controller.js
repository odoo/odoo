/** @odoo-module **/

import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller";
import { patch } from "@web/core/utils/patch";

patch(AttendeeCalendarController.prototype, {
    /**
     * Add the opportunity name from which the user came from if
     * there is one
     */
    getOpportunityName() {
        if (!this.props.context.default_opportunity_id) {
            return undefined;
        }
        return this.props.context.default_name;
    },
});
