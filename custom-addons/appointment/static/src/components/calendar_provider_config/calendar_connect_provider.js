/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarConnectProvider } from "@calendar/components/calendar_provider_config/calendar_connect_provider";


patch(CalendarConnectProvider.prototype, {
    /**
     * Sets onboarding step state as completed.
     *
     * @override
     */
    async _beforeLeaveContext () {
        return this.orm.call(
            'onboarding.onboarding.step',
            'action_validate_step',
            ['appointment.appointment_onboarding_configure_calendar_provider_step']
        );
    }
});
