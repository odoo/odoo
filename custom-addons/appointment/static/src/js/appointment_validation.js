/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import { findInvalidEmailFromText } from  "./utils.js"
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.appointmentValidation = publicWidget.Widget.extend({
    selector: '.o_appointment_validation_details',
    events: {
        'click .o_appointment_guest_addition_open': '_onGuestAdditionOpen',
        'click .o_appointment_guest_discard': '_onGuestDiscard',
        'click .o_appointment_guest_add': '_onGuestAdd',
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
            jsonrpc(`/calendar/${accessToken}/add_attendees_from_emails`, {
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
