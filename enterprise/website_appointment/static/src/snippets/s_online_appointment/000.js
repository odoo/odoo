/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";


const OnlineAppointmentCtaWidget = publicWidget.Widget.extend({
    selector: '.s_online_appointment',
    disabledInEditableMode: true,
    events: {
        'click': '_onCtaClick'
    },
    _onCtaClick: function (ev) {
        let url = '/appointment';

        const selectedAppointments = ev.target.closest('.s_online_appointment').dataset.appointmentTypes;
        const appointmentsTypeIds = selectedAppointments ? JSON.parse(selectedAppointments) : [];
        const nbSelectedAppointments = appointmentsTypeIds.length;
        if (nbSelectedAppointments === 1) {
            url += `/${encodeURIComponent(appointmentsTypeIds[0])}`;
            const selectedUsers = ev.target.closest('.s_online_appointment').dataset.staffUsers;
            if (JSON.parse(selectedUsers).length) {
                url += `?filter_staff_user_ids=${encodeURIComponent(selectedUsers)}`;
            }
        } else if (nbSelectedAppointments > 1) {
            url += `?filter_appointment_type_ids=${encodeURIComponent(selectedAppointments)}`;
        }
        window.location = url;
    },
});

publicWidget.registry.online_appointment = OnlineAppointmentCtaWidget;

export default OnlineAppointmentCtaWidget;
