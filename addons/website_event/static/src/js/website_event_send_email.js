/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { checkEmailValidity } from  "@mail/utils/common/format";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.websiteEventSendEmail = publicWidget.Widget.extend({
    selector: '.o_wevent_send_by_email_widget',
    events: {
        'click .o_wevent_js_send_email': '_onSendEmailClick',
        'click .o_wevent_send_by_email_info .btn-close': '_onCloseInfoClick',
    },

    init() {
        this.notification = this.bindService("notification");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onSendEmailClick: async function (ev) {
        ev.target.insertAdjacentHTML('afterbegin', '<i class="fa fa-circle-o-notch fa-spin me-1"></i>');
        ev.target.disabled = true;

        const attendeesIds = JSON.parse(ev.target.dataset.attendeesIds) || [];
        const eventId = parseInt(ev.target.dataset.eventId, 10);
        const ticketsHash = ev.target.dataset.ticketsHash;
        const emails = document.querySelector('#o_wevent_send_by_email_input').value;
        const emailInfo = checkEmailValidity(', ', emails)

        if (emails === "" || emailInfo.invalidEmails.length) {
            this._showError();
        } else {
            this._hideError();
            await rpc(`/event/${ eventId }/my_tickets_by_email`, {
                'emails': emails,
                'registration_ids': attendeesIds,
                'tickets_hash': ticketsHash,
            });
            this._showInfoMsg();
        }
        ev.target.disabled = false;
        ev.target.querySelector('.fa-spin').remove();
    },

    /**
     * @private
     * Show error message if email is invalid by adding the bootstrap class
     * 'is-invalid' on the input field and its parent. The parent is the div that
     * contains the input field and the error message and has the class 'has-validation'.
     * For more information : https://getbootstrap.com/docs/5.3/forms/validation/#server-side
     */
    _showError: function () {
        const inputElement = document.querySelector('#o_wevent_send_by_email_input');
        inputElement.classList.add('is-invalid');
        inputElement.parentElement.classList.add('is-invalid');
    },

    /**
     * @private
     * Hide error message if email is valid by removing the bootstrap class
     * 'is-invalid' on the input field and its parent. The parent is the div that
     * contains the input field and the error message and has the class 'has-validation'.
     * For more information : https://getbootstrap.com/docs/5.3/forms/validation/#server-side
     */
    _hideError: function () {
        const inputElement = document.querySelector('#o_wevent_send_by_email_input');
        inputElement.classList.remove('is-invalid');
        inputElement.parentElement.classList.remove('is-invalid');
    },

    _showInfoMsg: function () {
        const inputMsgDiv = document.querySelector('.o_wevent_send_by_email_widget div');
        inputMsgDiv.classList.add('d-none');
        const infoMsgDiv = document.querySelector('.o_wevent_send_by_email_info');
        infoMsgDiv.classList.remove('d-none');
    },

    _onCloseInfoClick: function () {
        const inputMsgDiv = document.querySelector('.o_wevent_send_by_email_widget div');
        inputMsgDiv.classList.remove('d-none');
        const infoMsgDiv = document.querySelector('.o_wevent_send_by_email_info');
        infoMsgDiv.classList.add('d-none');
    },
});

export default {
    websiteEventSendEmail: publicWidget.registry.websiteEventSendEmail,
};
