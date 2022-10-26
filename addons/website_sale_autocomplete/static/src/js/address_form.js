/** @odoo-module */

import publicWidget from 'web.public.widget';
import { DropPrevious } from 'web.concurrency';
import { debounce } from "@web/core/utils/timing";
import { qweb as QWeb } from 'web.core';

publicWidget.registry.AddressForm = publicWidget.Widget.extend({
    selector: '.oe_cart .checkout_autoformat:has(input[name="street"][data-autocomplete-enabled="1"])',
    events: {
        'input input[name="street"]': '_onChangeStreet',
        'click .js_autocomplete_result': '_onClickAutocompleteResult'
    },
    init: function() {
        this.streetAndNumberInput = document.querySelector('input[name="street"]');
        this.cityInput = document.querySelector('input[name="city"]');
        this.zipInput = document.querySelector('input[name="zip"]');
        this.countrySelect = document.querySelector('select[name="country_id"]');
        this.stateSelect = document.querySelector('select[name="state_id"]');
        this.dp = new DropPrevious();
        this.sessionId = this._generateUUID();

        this._onChangeStreet = debounce(this._onChangeStreet, 200);
        this._super.apply(this, arguments);
    },

     /**
      * Used to generate a unique session ID for the places API.
      *
      * @private
      */
    _generateUUID: function() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (Math.random() * 16) | 0, v = c == "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
        });
    },

    _hideAutocomplete: function (inputContainer) {
        const dropdown = inputContainer.querySelector('.dropdown-menu');
        if (dropdown) {
            dropdown.remove();
        }
    },

    _onChangeStreet: async function (ev) {
        const inputContainer = ev.currentTarget.parentNode;
        if (ev.currentTarget.value.length >= 5) {
            this.dp.add(
                this._rpc({
                    route: '/autocomplete/address',
                    params: {
                        partial_address: ev.currentTarget.value,
                        session_id: this.sessionId || null
                    }
                })).then((response) => {
                    this._hideAutocomplete(inputContainer);
                    inputContainer.appendChild($(QWeb.render("website_sale_autocomplete.AutocompleteDropDown", {
                        results: response.results
                    }))[0]);
                    if (response.session_id) {
                        this.sessionId = response.session_id;
                    }
                }
            );
        } else {
            this._hideAutocomplete(inputContainer);
        }
    },

    _onClickAutocompleteResult: async function(ev) {
        const dropDown = ev.currentTarget.parentNode;

        const spinner = document.createElement('div');
        dropDown.innerText = '';
        dropDown.classList.add('d-flex', 'justify-content-center', 'align-items-center');
        spinner.classList.add('spinner-border', 'text-warning', 'text-center', 'm-auto');
        dropDown.appendChild(spinner);

        const address = await this._rpc({
            route: '/autocomplete/address_full',
            params: {
                address: ev.currentTarget.innerText,
                google_place_id: ev.currentTarget.dataset.googlePlaceId,
                session_id: this.sessionId || null
            }
        });
        if (address.formatted_street_number) {
            this.streetAndNumberInput.value = address.formatted_street_number;
        }
        // Text fields, empty if no value in order to avoid the user missing old data.
        this.zipInput.value = address.zip || '';
        this.cityInput.value = address.city || '';

        // Selects based on odoo ids
        if (address.country) {
            this.countrySelect.value = address.country;
            // Let the state select know that the country has changed so that it may fetch the correct states or disappear.
            this.countrySelect.dispatchEvent(new Event('change', {bubbles: true}));
        }
        if (address.state) {
            // Waits for the stateSelect to update before setting the state.
            new MutationObserver((entries, observer) => {
                this.stateSelect.value = address.state;
                observer.disconnect();
            }).observe(this.stateSelect, {
                childList: true, // Trigger only if the options change
            });
        }
        dropDown.remove();
    },
});
