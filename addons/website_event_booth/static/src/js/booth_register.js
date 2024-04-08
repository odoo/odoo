/** @odoo-module **/

import { renderToElement, renderToFragment } from "@web/core/utils/render";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.boothRegistration = publicWidget.Widget.extend({
    selector: '.o_wbooth_registration',
    events: {
        'change input[name="booth_category_id"]': '_onChangeBoothType',
        'change .form-check > input[type="checkbox"]': '_onChangeBooth',
        'click .o_wbooth_registration_submit': '_onSubmitBoothSelectionClick',
        'click .o_wbooth_registration_confirm': '_onConfirmRegistrationClick',
    },

    start() {
        this.eventId = parseInt(this.el.dataset.eventId);
        this.activeBoothCategoryId = false;
        this.boothCache = {};
        this.boothsFirstRendering = true;
        this.selectedBoothIds = [];
        return this._super.apply(this, arguments).then(() => {
            this.selectedBoothCategory = this.el.querySelector('input[name="booth_category_id"]:checked');
            if (this.selectedBoothCategory) {
                this.selectedBoothIds = this.el.querySelector('.o_wbooth_booths').dataset.selectedBoothIds.split(',').map(Number);
                this.activeBoothCategoryId = this.selectedBoothCategory.value;
                this._fetchBoothsAndUpdateUI();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _check_booths_availability(eventBoothIds) {
        const self = this;
        return rpc("/event/booth/check_availability", {
            event_booth_ids: eventBoothIds,
        }).then(function (result) {
            if (result.unavailable_booths.length) {
                self.el.querySelectorAll('input[name="event_booth_ids"]').forEach(function (el) {
                    if (result.unavailable_booths.includes(parseInt(el.value))) {
                        el.closest('.form-check').classList.add('text-danger');
                    }
                });
                self.el.querySelector('.o_wbooth_unavailable_booth_alert').classList.remove('d-none');
                return Promise.resolve(false);
            }
            return Promise.resolve(true);
        })
    },

    _countSelectedBooths() {
        return this.el.querySelectorAll('.form-check > input[type="checkbox"]:checked').length;
    },

    _fillBooths() {
        const boothsElem = this.el.querySelector('.o_wbooth_booths');
        boothsElem.replaceChildren(renderToFragment('event_booth_checkbox_list', {
            'event_booth_ids': this.boothCache[this.activeBoothCategoryId],
            'selected_booth_ids': this.boothsFirstRendering ? this.selectedBoothIds : [],
        }));

        this.boothsFirstRendering = false;
    },

    /**
     * Check if the confirmation form is valid by testing each of its inputs
     *
     * @private
     * @param form
     * @return {boolean} - true if no errors else false
     */
    _isConfirmationFormValid(form) {
        const formErrors = [];

        form.querySelectorAll('.form-control').forEach(function (input) {
            input.classList.remove('is-invalid');
            if (input.length && !input.checkValidity()) {
                input.classList.add('is-invalid');
                formErrors.push('invalidFormInputs');
            }
        });

        this._updateErrorDisplay(formErrors);
        return formErrors.length === 0;
    },

    _showBoothCategoryDescription() {
        this.el.querySelectorAll('.o_wbooth_booth_description').forEach(el => el.classList.add('d-none'));
        this.el.querySelector('#o_wbooth_booth_description_' + this.activeBoothCategoryId).classList.remove('d-none');
    },

    /**
     * Display the errors with a custom message when confirming
     * the registration if there is any.
     *
     * @private
     * @param errors
     */
    _updateErrorDisplay(errors) {
        this.el.querySelector('.o_wbooth_registration_error_section').classList.toggle('d-none', !errors.length);

        let errorMessages = [];
        let errorMessage = this.el.querySelector('.o_wbooth_registration_error_message');

        if (errors.includes('invalidFormInputs')) {
            errorMessages.push(_t("Please fill out the form correctly."));
        }

        if (errors.includes('boothError')) {
            errorMessages.push(_t("Booth registration failed."));
        }

        if (errors.includes('boothCategoryError')) {
            errorMessages.push(_t("The booth category doesn't exist."));
        }

        errorMessage.textContent = errorMessages.join(' ');
        errorMessage.dispatchEvent(new Event('change'));
    },

    _updateUiAfterBoothCategoryChange() {
        this._fillBooths();
        this._showBoothCategoryDescription();
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _updateUiAfterBoothChange(boothCount) {
        let button = this.el.querySelector('button.o_wbooth_registration_submit');
        button.disabled = !boothCount;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onChangeBooth(ev) {
        ev.currentTarget.closest('.form-check').classList.remove('text-danger');
        this._updateUiAfterBoothChange(this._countSelectedBooths());
    },

    _onChangeBoothType(ev) {
        ev.preventDefault();
        this.activeBoothCategoryId = parseInt(ev.currentTarget.value);
        this._fetchBoothsAndUpdateUI();
    },

    /**
     * Load all the booths related to the activeBoothCategoryId booth category and
     * add them to a local dictionary to avoid making rpc each time the
     * user change the booth category.
     *
     * Then the selection input will be filled with the fetched booth values.
     *
     * @private
     */
    _fetchBoothsAndUpdateUI() {
        if (this.boothCache[this.activeBoothCategoryId] === undefined) {
            var self = this;
            rpc('/event/booth_category/get_available_booths', {
                event_id: this.eventId,
                booth_category_id: this.activeBoothCategoryId,
            }).then(function (result) {
                self.boothCache[self.activeBoothCategoryId] = result;
                self._updateUiAfterBoothCategoryChange();
            });
        } else {
            this._updateUiAfterBoothCategoryChange();
        }
    },

    async _onSubmitBoothSelectionClick(ev) {
        ev.preventDefault();
        let form = this.el.querySelector('.o_wbooth_registration_form');
        let event_booth_ids = Array.from(this.el.querySelectorAll('input[name=event_booth_ids]:checked')).map(function (el) {
            return parseInt(el.value);
        });
        if (await this._check_booths_availability(event_booth_ids)) {
            form.submit();
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

        ev.currentTarget.classList.add('disabled');
        ev.currentTarget.disabled = true;

        const form = this.el.querySelector('#o_wbooth_contact_details_form');
        if (this._isConfirmationFormValid(form)) {
            const formData = new FormData(form);
            const response = await fetch(`/event/${encodeURIComponent(this.el.dataset.eventId)}/booth/confirm`, {
                method: 'POST',
                body: formData,
            });

            const jsonResponse = await response.json();
            if (jsonResponse.success) {
                this.el.querySelector('.o_wevent_booth_order_progress').remove();
                const boothCategoryId = this.el.querySelector('input[name=booth_category_id]').value;
                form.replaceWith(renderToElement('event_booth_registration_complete', {
                    'booth_category_id': boothCategoryId,
                    'event_id': this.eventId,
                    'event_name': jsonResponse.event_name,
                    'contact': jsonResponse.contact,
                }));
            } else if (jsonResponse.redirect) {
                window.location.href = jsonResponse.redirect;
            } else if (jsonResponse.error) {
                this._updateErrorDisplay(jsonResponse.error);
            }
        }

        ev.currentTarget.classList.remove('disabled');
        ev.currentTarget.disabled = false;
    },

});

export default publicWidget.registry.boothRegistration;
