/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.appointmentTypeSelect = publicWidget.Widget.extend({
    selector: '.o_appointment_choice',
    events: {
        'change select[id="appointment_type_id"]': '_onAppointmentTypeChange',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        // Check if we cannot replace this by a async handler once the related
        // task is merged in master
        this._onAppointmentTypeChange = debounce(this._onAppointmentTypeChange, 250);
        this.rpc = this.bindService("rpc");
    },

    /**
     * @override
     */
    start: function () {
        return this._super(...arguments).then(() => {
            // Load an image when no appointment types are found
            this.$el.find('.o_appointment_svg i').replaceWith(renderToElement('Appointment.appointment_svg', {}));
            this.$el.find('.o_appointment_not_found div').removeClass('d-none');
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * On appointment type change: adapt appointment intro text and available
     * users. (if option enabled)
     *
     * @override
     * @param {Event} ev
     */
    _onAppointmentTypeChange: function (ev) {
        var self = this;
        const appointmentTypeID = $(ev.target).val();
        const filterAppointmentTypeIds = this.$("input[name='filter_appointment_type_ids']").val();
        const filterUserIds = this.$("input[name='filter_staff_user_ids']").val();
        const filterResourceIds = this.$("input[name='filter_resource_ids']").val();
        const inviteToken = this.$("input[name='invite_token']").val();
        self.$(".o_appointment_appointments_list_form").attr('action', `/appointment/${appointmentTypeID}${window.location.search}`);

        this.rpc(`/appointment/${appointmentTypeID}/get_message_intro`, {
            invite_token: inviteToken,
            filter_appointment_type_ids: filterAppointmentTypeIds,
            filter_staff_user_ids: filterUserIds,
            filter_resource_ids: filterResourceIds,
        }).then(function (message_intro) {
            self.$('.o_appointment_intro').empty().append(message_intro);
        });
    },
});
