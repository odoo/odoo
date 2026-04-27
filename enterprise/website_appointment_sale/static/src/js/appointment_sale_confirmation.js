/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { user } from "@web/core/user";

publicWidget.registry.appointmentSaleConfirmation = publicWidget.Widget.extend({
    selector: '.o_wappointment_sale_confirmation_card',

    /**
     * Store in local storage the appointment booked for the appointment type.
     * This value is used later to display information on the upcoming appointment
     * if an appointment is already taken. If the user is logged don't store anything
     * as everything is computed by the /appointment/get_upcoming_appointments route.
     * @override
     */
    start: function() {
        return this._super(...arguments).then(() => { 
            if (user.userId) {
                return;
            }
            const eventAccessToken = this.el.dataset.eventAccessToken;
            const allAppointmentsToken = JSON.parse(localStorage.getItem('appointment.upcoming_events_access_token')) || [];
            if (eventAccessToken && !allAppointmentsToken.includes(eventAccessToken)) {
                allAppointmentsToken.push(eventAccessToken);
                localStorage.setItem('appointment.upcoming_events_access_token', JSON.stringify(allAppointmentsToken));
            }
        });
    },
});
