/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.appointmentTypeSelect = publicWidget.Widget.extend({
    selector: '.o_appointment_choice',
    events: {
        'change select[id="appointment_type_id"]': '_onAppointmentTypeChange',
        'click .o_appointment_select_button': '_onAppointmentTypeSelected',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        // Check if we cannot replace this by a async handler once the related
        // task is merged in master
        this._onAppointmentTypeChange = debounce(this._onAppointmentTypeChange, 250);
    },

    /**
     * @override
     */
    start: function () {
        return this._super(...arguments).then(() => {
            // Load an image when no appointment types are found
            this.el.querySelector(".o_appointment_svg i")?.replaceWith(renderToElement('Appointment.appointment_svg', {}));
            this.el
                .querySelectorAll(".o_appointment_not_found div")
                .forEach((el) => el.classList.remove("d-none"));
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
        const appointmentTypeID = ev.target.value;
        const filterAppointmentTypeIds = this.el.querySelector(
            "input[name='filter_appointment_type_ids']"
        ).value;
        const filterUserIds = this.el.querySelector("input[name='filter_staff_user_ids']").value;
        const filterResourceIds = this.el.querySelector("input[name='filter_resource_ids']").value;
        const inviteToken = this.el.querySelector("input[name='invite_token']").value;

        rpc(`/appointment/${appointmentTypeID}/get_message_intro`, {
            invite_token: inviteToken,
            filter_appointment_type_ids: filterAppointmentTypeIds,
            filter_staff_user_ids: filterUserIds,
            filter_resource_ids: filterResourceIds,
        }).then(function (message_intro) {
            const parsedElements = new DOMParser().parseFromString(message_intro, 'text/html').body.childNodes;
            self.el.querySelector(".o_appointment_intro")?.replaceChildren(...parsedElements);
        });
    },

    _onAppointmentTypeSelected: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const optionSelected = this.el.querySelector('select').selectedOptions[0];
        window.location = optionSelected.dataset.appointmentUrl;
    },
});
