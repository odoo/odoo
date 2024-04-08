/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

publicWidget.registry.websiteEventTrackProposalForm = publicWidget.Widget.extend({
    selector: '.o_website_event_track_proposal_form',
    events: {
        'click .o_wetrack_add_contact_information_checkbox': '_onAdvancedContactToggle',
        'input input[name="partner_name"]': '_onPartnerNameInput',
        'click .o_wetrack_proposal_submit_button': '_onProposalFormSubmit',
    },

    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        this.useAdvancedContact = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Evaluate and return validity of form input fields:
     * - 1) error 'invalidFormInputs' : Invalid ones are marked as is-invalid and o_wetrack_input_error.
     * - 2) error 'noContactMean' : Contact mean fields are marked as is-invalid and contact
     * section as o_wetrack_no_contact_mean_error if none of them is filled.
     *
     * @private
     * @returns {Boolean} - True if no error remain, false otherwise
     */
    _isFormValid: function () {
        var formErrors = [];

        // 1) Valid Form Inputs
        Array.from(document.querySelectorAll('.form-control')).forEach(function (formControl) {
            // Validate current input, if not select2 field.
            var inputs = formControl.classList.contains('o_wetrack_select2_tags') ? [] : [formControl];
            var invalidInputs = inputs.filter(function (input) {
                return !input.checkValidity();
            });

            formControl.classList.remove('o_wetrack_input_error', 'is-invalid');
            if (invalidInputs.length) {
                formControl.classList.add('o_wetrack_input_error', 'is-invalid');
                formErrors.push('invalidFormInputs');
            }
        });

        // 2) Advanced Contact Must Have a Contact Mean
        if (this.useAdvancedContact) {
            var hasContactMean = document.querySelector('.o_wetrack_contact_phone_input').value ||
                document.querySelector('.o_wetrack_contact_email_input').value;
            if (!hasContactMean) {
                document.querySelector('.o_wetrack_contact_information').classList.add('o_wetrack_no_contact_mean_error');
                document.querySelector('.o_wetrack_contact_mean').classList.add('is-invalid');
                formErrors.push('noContactMean');
            } else {
                document.querySelector('.o_wetrack_contact_information').classList.remove('o_wetrack_no_contact_mean_error');
                Array.from(document.querySelectorAll('.o_wetrack_contact_mean:not(".o_wetrack_input_error")')).forEach(function (el) {
                    el.classList.remove('is-invalid');
                });
            }
        }

        // Form Validity and Error Display
        this._updateErrorDisplay(formErrors);
        return formErrors.length === 0;
    },

    /**
     * If there are still errors in form, display the error section and
     * compose the error message accordingly.
     *
     * @private
     * @param {Array} errors - Names of errors still present in form.
     */
    _updateErrorDisplay: function (errors) {

        document.querySelector('.o_wetrack_proposal_error_section').classList.toggle('d-none', !errors.length);

        var errorMessages = [];
        var errorElement = document.querySelector('.o_wetrack_proposal_error_message');

        if (errors.includes('invalidFormInputs')) {
            errorMessages.push(_t('Please fill out the form correctly.'));
        }

        if (errors.includes('noContactMean')) {
            errorMessages.push(_t('Please enter either a contact email address or a contact phone number.'));
        }

        if (errors.includes('forbidden')) {
            errorMessages.push(_t('You cannot access this page.'));
        }

        errorElement.textContent = errorMessages.join(' ');
        errorElement.dispatchEvent(new Event('change'));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Display / Hide Additional Contact Information section when toggling
     * the checkbox on the form o_wetrack_add_contact_information_checkbox.
     * Also empty the email to prevent hidden email format error.
     *
     * @private
     * @param {Event} ev
     */
    _onAdvancedContactToggle: function (ev) {
        this.useAdvancedContact = !this.useAdvancedContact;
        var contactName = document.querySelector(".o_wetrack_contact_name_input");
        var advancedInformation = document.querySelector('.o_wetrack_contact_information');

        if (this.useAdvancedContact) {
            advancedInformation.classList.remove('d-none');
            contactName.setAttribute("required", "True");
        } else {
            document.querySelector('.o_wetrack_contact_email_input').value = '';
            advancedInformation.classList.add('d-none');
            contactName.removeAttribute("required");
        }
    },

    /**
     * Propagates the new input on speaker name to contact name, as long as the latter
     * is the start of partner name. Otherwise, do not modify existing contact name.
     *
     * @private
     * @param {Event} ev
     */
    _onPartnerNameInput: function (ev) {
        var partnerNameText = ev.currentTarget.value;
        var contactNameInput = document.querySelector(".o_wetrack_contact_name_input");
        var contactNameText = contactNameInput.value;
        if (partnerNameText.startsWith(contactNameText)) {
            contactNameInput.value = partnerNameText;
            contactNameInput.dispatchEvent(new Event('change'));
        }
    },

    /**
     * Submits the form if no errors are present in the form after validation.
     *
     * If the submission succeeds, we replace the form with a template containing a small success
     * message.
     *
     * Then we scroll to the position of the success message so that the user can see it.
     * To do that we have to compute the position of the beginning of the element, relatively to its
     * position and the amount already scrolled, then subtract the floating header menu.
     *
     * @private
     * @param {Event} ev
     */
    _onProposalFormSubmit: async function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        // Prevent further clicking
        var submitButton = this.el.querySelector('.o_wetrack_proposal_submit_button');
        submitButton.classList.add('disabled');
        submitButton.setAttribute('disabled', 'disabled');

        // Submission of the form if no errors remain
        if (this._isFormValid()) {
            const formData = new FormData(this.el);

            const response = await fetch(`/event/${encodeURIComponent(this.el.dataset.eventId)}/track_proposal/post`, {
                method: 'POST',
                body: formData
            });

            const jsonResponse = await response.json();
            if (jsonResponse.success) {
                const offsetTop = (document.querySelector("#wrapwrap").scrollTop || 0) + this.el.offsetTop;
                const floatingMenuHeight = (document.querySelector('.o_header_standard').offsetHeight || 0) +
                    (document.querySelector('#oe_main_menu_navbar').offsetHeight || 0);
                this.el.outerHTML = renderToElement('event_track_proposal_success');
                document.querySelector('#wrapwrap').scrollTop = offsetTop - floatingMenuHeight;
            } else if (jsonResponse.error) {
                this._updateErrorDisplay([jsonResponse.error]);
            }
        }

        // Restore button
        submitButton.removeAttribute('disabled');
        submitButton.classList.remove('disabled');
    },
});

export default publicWidget.registry.websiteEventTrackProposalForm;
