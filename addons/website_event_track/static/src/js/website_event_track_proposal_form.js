odoo.define('website_event_track.website_event_track_proposal_form', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var QWeb = core.qweb;
var _t = core._t;

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
        this.$('.form-control').each(function () {
            var $formControl = $(this);
            // Validate current input, if not select2 field.
            var inputs = $formControl.not('.o_wetrack_select2_tags');
            var invalidInputs = inputs.toArray().filter(function (input) {
                return !input.checkValidity();
            });

            $formControl.removeClass('o_wetrack_input_error is-invalid');
            if (invalidInputs.length) {
                $formControl.addClass('o_wetrack_input_error is-invalid');
                formErrors.push('invalidFormInputs');
            }
        });

        // 2) Advanced Contact Must Have a Contact Mean
        if (this.useAdvancedContact) {
            var hasContactMean = this.$('.o_wetrack_contact_phone_input').val() ||
                this.$('.o_wetrack_contact_email_input').val();
            if (!hasContactMean) {
                this.$('.o_wetrack_contact_information').addClass('o_wetrack_no_contact_mean_error');
                this.$('.o_wetrack_contact_mean').addClass('is-invalid');
                formErrors.push('noContactMean');
            } else {
                this.$('.o_wetrack_contact_information').removeClass('o_wetrack_no_contact_mean_error');
                this.$('.o_wetrack_contact_mean:not(".o_wetrack_input_error")').removeClass('is-invalid');
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

        this.$('.o_wetrack_proposal_error_section').toggleClass('d-none', !errors.length);

        var errorMessages = [];
        var $errorElement = this.$('.o_wetrack_proposal_error_message');

        if (errors.includes('invalidFormInputs')) {
            errorMessages.push(_t('Please fill out the form correctly.'));
        }

        if (errors.includes('noContactMean')) {
            errorMessages.push(_t('Please enter either a contact email address or a contact phone number.'));
        }

        if (errors.includes('forbidden')) {
            errorMessages.push(_t('You cannot access this page.'));
        }

        $errorElement.text(errorMessages.join(' ')).change();
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
        var $contactName = this.$(".o_wetrack_contact_name_input")[0];
        var $advancedInformation = this.$('.o_wetrack_contact_information');

        if (this.useAdvancedContact) {
            $advancedInformation.removeClass('d-none');
            $contactName.setAttribute("required", "True");
        } else {
            this.$('.o_wetrack_contact_email_input').val('').change();
            $advancedInformation.addClass('d-none');
            $contactName.removeAttribute("required");
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
        var partnerNameText = $(ev.currentTarget).val();
        var contactNameText = this.$(".o_wetrack_contact_name_input").val();
        if (partnerNameText.startsWith(contactNameText)) {
            this.$(".o_wetrack_contact_name_input").val(partnerNameText).change();
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
        this.$target.find('.o_wetrack_proposal_submit_button')
            .addClass('disabled')
            .attr('disabled', 'disabled');

        // Submission of the form if no errors remain
        if (this._isFormValid()) {
            const formData = new FormData(this.$el[0]);

            const response = await $.ajax({
                url: `/event/${this.$el.data('eventId')}/track_proposal/post`,
                data: formData,
                processData: false,
                contentType: false,
                type: 'POST'
            });

            const jsonResponse = response && JSON.parse(response);
            if (jsonResponse.success) {
                const offsetTop = ($("#wrapwrap").scrollTop() || 0) + this.$el.offset().top;
                const floatingMenuHeight = ($('.o_header_standard').height() || 0) +
                    ($('#oe_main_menu_navbar').height() || 0);
                this.$el.replaceWith($(QWeb.render('event_track_proposal_success')));
                $('#wrapwrap').scrollTop(offsetTop - floatingMenuHeight);
            } else if (jsonResponse.error) {
                this._updateErrorDisplay([jsonResponse.error]);
            }
        }

        // Restore button
        this.$target.find('.o_wetrack_proposal_submit_button')
            .removeAttr('disabled')
            .removeClass('disabled');
    },
});

return publicWidget.registry.websiteEventTrackProposalForm;

});
