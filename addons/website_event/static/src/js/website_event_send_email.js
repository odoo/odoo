/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { extractEmailValidity } from  "@mail/utils/common/format";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteEventSendEmail = publicWidget.Widget.extend({
    selector: '.o_wevent_send_by_email_widget',
    events: {
        'click .o_wevent_send_by_email_button': '_onSendEmailButtonClick',
        'click .o_wevent_send_by_email_info .btn-close': '_onCloseInfoClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onSendEmailButtonClick: async function (ev) {
        ev.target.getElementsByTagName('i')[0].classList.remove('d-none');
        ev.target.setAttribute('disabled', '');

        const attendeesIds = JSON.parse(ev.target.dataset.attendeesIds) || [];
        const eventId = parseInt(ev.target.dataset.eventId);
        const ticketsHash = ev.target.dataset.ticketsHash;
        const emails = document.querySelector('#o_wevent_send_by_email_input').value;
        const emailInfo = extractEmailValidity(', ', emails)

        if (emails === "" || emailInfo.invalidEmails.length) {
            this._showEmailError();
        } else {
            this._hideEmailError();
            await rpc(`/event/${ eventId }/my_tickets_by_email`, {
                'emails': emails,
                'registration_ids': attendeesIds,
                'tickets_hash': ticketsHash,
            });
            this._showInfoMsg();
        }
        ev.target.removeAttribute('disabled');
        ev.target.getElementsByTagName('i')[0].classList.add('d-none');
    },

    /**
     * @private
     * Show error message if email is invalid by adding the bootstrap class
     * 'is-invalid' on the input field and its parent. The parent is the div that
     * contains the input field and the error message and has the class 'has-validation'.
     * For more information : https://getbootstrap.com/docs/5.3/forms/validation/#server-side
     */
    _showEmailError: function () {
        const emailInputElement = document.querySelector('#o_wevent_send_by_email_input');
        emailInputElement.classList.add('is-invalid');
        emailInputElement.parentElement.classList.add('is-invalid');
    },

    /**
     * @private
     * Hide error message if email is valid by removing the bootstrap class
     * 'is-invalid' on the input field and its parent. The parent is the div that
     * contains the input field and the error message and has the class 'has-validation'.
     * For more information : https://getbootstrap.com/docs/5.3/forms/validation/#server-side
     */
    _hideEmailError: function () {
        const emailInputElement = document.querySelector('#o_wevent_send_by_email_input');
        emailInputElement.classList.remove('is-invalid');
        emailInputElement.parentElement.classList.remove('is-invalid');
    },

    _showInfoMsg: function () {
        const emailInputContainer = document.querySelector('.o_wevent_send_by_email_input_container');
        const infoMessageElement = document.querySelector('.o_wevent_send_by_email_info');
        emailInputContainer.classList.add('d-none');
        infoMessageElement.classList.remove('d-none');
    },

    _onCloseInfoClick: function () {
        const emailInputContainer = document.querySelector('.o_wevent_send_by_email_input_container');
        const emailInputElement = document.querySelector('#o_wevent_send_by_email_input');
        const infoMessageElement = document.querySelector('.o_wevent_send_by_email_info');
        emailInputElement.value = '';
        emailInputContainer.classList.remove('d-none');
        infoMessageElement.classList.add('d-none');
    },
});

export default {
    websiteEventSendEmail: publicWidget.registry.websiteEventSendEmail,
};
