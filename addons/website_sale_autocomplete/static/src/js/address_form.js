import { googlePlacesSession } from "@google_address_autocomplete/google_places_session";
import { KeepLast } from "@web/core/utils/concurrency";
import { renderToElement } from "@web/core/utils/render";
import { debounce } from "@web/core/utils/timing";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.AddressForm = publicWidget.Widget.extend({
    selector: '.oe_cart .checkout_autoformat',
    selectorHas: 'input[name="street"][data-autocomplete-enabled="1"]',
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
        this.keepLast = new KeepLast();

        this._onChangeStreet = debounce(this._onChangeStreet, 200);
        this._super.apply(this, arguments);
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
            this.keepLast.add(
                googlePlacesSession.getAddressPropositions({
                    partial_address: ev.currentTarget.value
                })).then((response) => {
                    this._hideAutocomplete(inputContainer);
                    inputContainer.appendChild(renderToElement("website_sale_autocomplete.AutocompleteDropDown", {
                        results: response.results
                    }));
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

        const address = await googlePlacesSession.getAddressDetails({
            address: ev.currentTarget.innerText,
            google_place_id: ev.currentTarget.dataset.googlePlaceId,
        });

        if (address.formatted_street_number) {
            this.streetAndNumberInput.value = address.formatted_street_number;
        }
        // Text fields, empty if no value in order to avoid the user missing old data.
        this.zipInput.value = address.zip || '';
        this.cityInput.value = address.city || '';

        // Selects based on odoo ids
        if (address.country) {
            this.countrySelect.value = address.country[0];
            // Let the state select know that the country has changed so that it may fetch the correct states or disappear.
            this.countrySelect.dispatchEvent(new Event('change', {bubbles: true}));
        }
        if (address.state) {
            // Waits for the stateSelect to update before setting the state.
            new MutationObserver((entries, observer) => {
                this.stateSelect.value = address.state[0];
                observer.disconnect();
            }).observe(this.stateSelect, {
                childList: true, // Trigger only if the options change
            });
        }
        dropDown.remove();
    },
});
