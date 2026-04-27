/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import { findInvalidEmailFromText } from  "./utils.js"
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

publicWidget.registry.appointmentValidation = publicWidget.Widget.extend({
    selector: '.o_appointment_validation_details',
    events: {
        'click .o_appointment_copy_link': '_onCopyVideocallLink',
        'click .o_appointment_guest_addition_open': '_onGuestAdditionOpen',
        'click .o_appointment_guest_discard': '_onGuestDiscard',
        'click .o_appointment_guest_add': '_onGuestAdd',
    },

    async _onCopyVideocallLink(ev) {
        const copyButtonEl = ev.target;
        const tooltip = Tooltip.getOrCreateInstance(copyButtonEl, {
            title: _t("Link Copied!"),
            trigger: "manual",
            placement: "right",
        });
        setTimeout(
            async () => await browser.navigator.clipboard.writeText(copyButtonEl.dataset.value)
        );
        tooltip.show();
        setTimeout(() => tooltip.hide(), 1200);
    },

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
            const eventStart = this.el.dataset.eventStart && deserializeDateTime(this.el.dataset.eventStart) || false;
            const allAppointmentsToken = JSON.parse(localStorage.getItem('appointment.upcoming_events_access_token')) || [];
            if (eventAccessToken && !allAppointmentsToken.includes(eventAccessToken) && eventStart && eventStart > luxon.DateTime.utc()) {
                allAppointmentsToken.push(eventAccessToken);
                localStorage.setItem('appointment.upcoming_events_access_token', JSON.stringify(allAppointmentsToken));
            }
        });
    },

    /**
     * This function will make the RPC call to add the guests from there email,
     * if a guest is unavailable then it will give us an error msg on the UI side with
     * the name of the unavailable guest.
     */
    _onGuestAdd: async function() {
        const guestEmails = this.el.querySelector('#o_appointment_input_guest_emails').value;
        const accessToken = this.el.querySelector('#access_token').value;
        const emailInfo = findInvalidEmailFromText(guestEmails)
        if (emailInfo.emailList.length > 10) {
            this._showErrorMsg(_t('You cannot invite more than 10 people'));
        } else if (emailInfo.invalidEmails.length) {
            this._showErrorMsg(_t('Invalid Email'));
        } else {
            this._hideErrorMsg();
            rpc(`/calendar/${accessToken}/add_attendees_from_emails`, {
                access_token: accessToken,
                emails_str: guestEmails,
            }).then(() => location.reload());
        }
    },

     /**
     * This function displays a textarea on the appointment validation page,
     * allowing users to enter guest emails if the allow_guest option is enabled.
     */
     _onGuestAdditionOpen: function(){
        const textArea = this.el.querySelector('#o_appointment_input_guest_emails');
        textArea.classList.remove('d-none');
        textArea.focus();
        this.el.querySelector('.o_appointment_guest_addition_open').classList.add('d-none');
        this.el.querySelector('.o_appointment_guest_add').classList.remove('d-none');
        this.el.querySelector('.o_appointment_guest_discard').classList.remove('d-none')
    },

    /**
     * This function will clear the guest email textarea at the appointment validation page
     * if allow_guest option is enabled.
     */
    _onGuestDiscard: function() {
        this._hideErrorMsg();
        const textArea = this.el.querySelector('#o_appointment_input_guest_emails');
        textArea.value = ""
        textArea.classList.add('d-none')
        this.el.querySelector('.o_appointment_guest_addition_open').classList.remove('d-none');
        this.el.querySelector('.o_appointment_guest_add').classList.add('d-none');
        this.el.querySelector('.o_appointment_guest_discard').classList.add('d-none');
    },

    _hideErrorMsg: function() {
        const errorMsgDiv = this.el.querySelector('.o_appointment_validation_error');
        errorMsgDiv.classList.add('d-none');
    },

    _showErrorMsg: function(errorMessage) {
        const errorMsgDiv = this.el.querySelector('.o_appointment_validation_error');
        errorMsgDiv.classList.remove('d-none');
        errorMsgDiv.querySelector('.o_appointment_error_text').textContent = errorMessage;
    },

});
