odoo.define('website_event_booth.booth_registration', function (require) {
'use strict';

var core = require('web.core');
var dom = require('web.dom');
var publicWidget = require('web.public.widget');
var QWeb = core.qweb;
var _t = core._t;

publicWidget.registry.boothRegistration = publicWidget.Widget.extend({
    selector: '.o_wbooth_registration',
    events: {
        'change input[name="booth_category_id"]': '_onChangeBoothType',
        'change .form-check > input[type="checkbox"]': '_onChangeBooth',
        'click .o_wbooth_registration_submit': '_onSubmitBoothSelectionClick',
        'click .o_wbooth_registration_confirm': '_onConfirmRegistrationClick',
    },

    start() {
        this.eventId = parseInt(this.$el.data('event-id'));
        this.activeType = false;
        this.boothCache = {};
        return this._super.apply(this, arguments).then(() => {
            this.$('input[name="booth_category_id"]:enabled:first').click();
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _check_booths_availability(eventBoothIds) {
        const self = this;
        return this._rpc({
            route: "/event/booth/check_availability",
            params: {
                event_booth_ids: eventBoothIds,
            },
        }).then(function (result) {
            if (result.unavailable_booths.length) {
                self.$('input[name="event_booth_ids"]').each(function (i, el) {
                    if (result.unavailable_booths.includes(parseInt(el.value))) {
                        $(el).closest('.form-check').addClass('text-danger');
                    }
                });
                self.$('.o_wbooth_unavailable_booth_alert').removeClass('d-none');
                return Promise.resolve(false);
            }
            return Promise.resolve(true);
        })
    },

    _countSelectedBooths() {
        return this.$('.form-check > input[type="checkbox"]:checked').length;
    },

    _fillBooths() {
        var $boothElem = this.$('.o_wbooth_booths');
        $boothElem.empty();
        $.each(this.boothCache[this.activeType], function (key, booth) {
            let $checkbox = dom.renderCheckbox({
                text: booth.name,
                prop: {
                    name: 'event_booth_ids',
                    value: booth.id
                }
            });
            $boothElem.append($checkbox);
        });
    },

    /**
     * Check if the confirmation form is valid by testing each of its inputs
     *
     * @private
     * @param $form
     * @return {boolean} - true if no errors else false
     */
    _isConfirmationFormValid($form) {
        const formErrors = [];

        $form.find('.form-control').each(function () {
            let input = $(this);
            input.removeClass('is-invalid');
            if (input.length && !input[0].checkValidity()) {
                input.addClass('is-invalid');
                formErrors.push('invalidFormInputs');
            }
        });

        this._updateErrorDisplay(formErrors);
        return formErrors.length === 0;
    },

    _showBoothCategoryDescription() {
        this.$('.o_wbooth_booth_description').addClass('d-none');
        this.$('#o_wbooth_booth_description_' + this.activeType).removeClass('d-none');
    },

    /**
     * Display the errors with a custom message when confirming
     * the registration if there is any.
     *
     * @private
     * @param errors
     */
    _updateErrorDisplay(errors) {
        this.$('.o_wbooth_registration_error_section').toggleClass('d-none', !errors.length);

        let errorMessages = [];
        let $errorMessage = this.$('.o_wbooth_registration_error_message');

        if (errors.includes('invalidFormInputs')) {
            errorMessages.push(_t("Please fill out the form correctly."));
        }

        if (errors.includes('boothError')) {
            errorMessages.push(_t("Booth registration failed."));
        }

        if (errors.includes('boothCategoryError')) {
            errorMessages.push(_t("The booth category doesn't exist."));
        }

        $errorMessage.text(errorMessages.join(' ')).change();
    },

    _updateUiAfterBoothCategoryChange() {
        this._fillBooths();
        this._showBoothCategoryDescription();
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _updateUiAfterBoothChange(boothCount) {
        let $button = this.$('button.o_wbooth_registration_submit');
        $button.attr('disabled', !boothCount);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeBooth(ev) {
        $(ev.currentTarget).closest('.form-check').removeClass('text-danger');
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    /**
     * Load all the booths related to the chosen booth category and
     * add them to a local dictionary to avoid making rpc each time the
     * user change the booth category.
     *
     * Then the selection input will be filled with the fetched booth values.
     *
     * @param ev
     * @private
     */
    _onChangeBoothType(ev) {
        ev.preventDefault();
        this.activeType = parseInt(ev.currentTarget.value);
        if (this.boothCache[this.activeType] === undefined) {
            var self = this;
            this._rpc({
                route: '/event/booth_category/get_available_booths',
                params: {
                    event_id: this.eventId,
                    booth_category_id: this.activeType,
                },
            }).then(function (result) {
                self.boothCache[self.activeType] = result;
                self._updateUiAfterBoothCategoryChange();
            });
        } else {
            this._updateUiAfterBoothCategoryChange();
        }
    },

    async _onSubmitBoothSelectionClick(ev) {
        ev.preventDefault();
        let $form = this.$('.o_wbooth_registration_form');
        let event_booth_ids = this.$('input[name=event_booth_ids]:checked').map(function () {
            return parseInt($(this).val());
        }).get();
        if (await this._check_booths_availability(event_booth_ids)) {
            $form.submit();
        }
    },

    /**
     * Submit the confirmation form if no errors are present after validation.
     *
     * If the submission succeed, we replace the form with a success message template.
     *
     * @param ev
     * @return {Promise<void>}
     * @private
     */
    async _onConfirmRegistrationClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();

        $(ev.currentTarget).addClass('disabled').attr('disabled', 'disabled');

        const $form = this.$('#o_wbooth_contact_details_form');
        if (this._isConfirmationFormValid($form)) {
            const formData = new FormData($form[0]);
            const response = await $.ajax({
                url: `/event/${this.$el.data('eventId')}/booth/confirm`,
                data: formData,
                processData: false,
                contentType: false,
                type: 'POST',
            });

            const jsonResponse = response && JSON.parse(response);
            if (jsonResponse.success) {
                $form.replaceWith($(QWeb.render('event_booth_registration_complete', {
                    'event_name': jsonResponse.event_name,
                    'contact': jsonResponse.contact,
                })));
            } else if (jsonResponse.redirect) {
                window.location.href = jsonResponse.redirect;
            } else if (jsonResponse.error) {
                this._updateErrorDisplay(jsonResponse.error);
            }
        }

        $(ev.currentTarget).removeClass('disabled').removeAttr('disabled');
    },

});

return publicWidget.registry.boothRegistration;
});
