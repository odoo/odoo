/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { findInvalidEmailFromText } from  "./utils.js"
import { _t } from "@web/core/l10n/translation";
import { addLoadingEffect } from '@web/core/utils/ui';

publicWidget.registry.appointmentForm = publicWidget.Widget.extend({
    selector: '.o_appointment_attendee_form',
    events: {
        'click div.o_appointment_add_guests button.o_appointment_input_guest_add': '_onAddGuest',
        'click div.o_appointment_add_guests button.o_appointment_input_guest_cancel': '_onHideGuest',
        'click .o_appointment_form_confirm_btn': '_onConfirmAppointment',
    },

    /**
     * Restore the attendee data from the local storage if the attendee doesn't have any partner data.
     */
    start: function () {
        return this._super(...arguments).then(() => {
            this.hasFormDefaultValues = this._getAttendeeFormData().some(([_, value]) => value !== '');
            if (!this.hasFormDefaultValues && localStorage.getItem('appointment.form.values')) {
                const attendeeData = JSON.parse(localStorage.getItem('appointment.form.values'));
                const form = this.el.querySelector('form.appointment_submit_form');
                for (const [name, value] of Object.entries(attendeeData)) {
                    const input = form.querySelector(`input[name="${name}"]`);
                    if (input) {
                        input.value = value;
                    }
                }
            }
        });
    },

    _getAttendeeFormData: function() {
        const formData = new FormData(this.el.querySelector('form.appointment_submit_form'));
        return Array.from(formData).filter(([key]) => ['name', 'phone', 'email'].includes(key));
    },

    /**
     * This function will show the guest email textarea where user can enter the
     * emails of the guests if allow_guests option is enabled.
     */
    _onAddGuest: function(){
        const textArea = this.el.querySelector('#o_appointment_input_guest_emails');
        textArea.classList.remove('d-none');
        textArea.focus();
        const addGuestDiv = this.el.querySelector('div.o_appointment_add_guests')
        addGuestDiv.querySelector('button.o_appointment_input_guest_add').classList.add('d-none')
        addGuestDiv.querySelector('button.o_appointment_input_guest_cancel').classList.remove('d-none')
    },

    _onConfirmAppointment: async function(event) {
        this._validateCheckboxes();
        const textArea = this.el.querySelector('#o_appointment_input_guest_emails');
        const appointmentForm = document.querySelector('.appointment_submit_form');
        if (textArea && textArea.value.trim() !== '') {
            let emailInfo = findInvalidEmailFromText(textArea.value);
            if (emailInfo.invalidEmails.length || emailInfo.emailList.length > 10) {
                const errorMessage = emailInfo.invalidEmails.length > 0 ? _t('Invalid Email') : _t("You cannot invite more than 10 people");
                this._showErrorMsg(errorMessage);
                return;
            } else {
                this._hideErrorMsg();
            }
        }
        if (appointmentForm.reportValidity()) {
            if (!this.hasFormDefaultValues) {
                const attendeeData = this._getAttendeeFormData();
                if (attendeeData.length) {
                    localStorage.setItem('appointment.form.values', JSON.stringify(Object.fromEntries(attendeeData)));
                }
            }
            appointmentForm.submit();
            addLoadingEffect(event.target);
        }
    },

    /**
     * This function will hide the guest email textarea if allow_guests option is enabled.
     */
    _onHideGuest: function() {
        this._hideErrorMsg();
        const textArea = this.el.querySelector('#o_appointment_input_guest_emails');
        textArea.classList.add('d-none')
        textArea.value = "";
        const addGuestDiv = this.el.querySelector('div.o_appointment_add_guests')
        addGuestDiv.querySelector('button.o_appointment_input_guest_add').classList.remove('d-none');
        addGuestDiv.querySelector('button.o_appointment_input_guest_cancel').classList.add('d-none');
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

    _validateCheckboxes: function() {
        this.el.querySelectorAll(".checkbox-group.required").forEach((groupEl) => {
            const checkboxEls = groupEl.querySelectorAll(".checkbox input");
            checkboxEls.forEach(
                (checkboxEl) =>
                    (checkboxEl.required = ![...checkboxEls].some(
                        (checkboxEl) => checkboxEl.checked
                    ))
            );
        });
    },
});
