/** @odoo-module */

import PublicWidget from '@web/legacy/js/public/public_widget';
import {_t} from '@web/core/l10n/translation';

export const PurchaseBankAccount = PublicWidget.Widget.extend({
    selector: '#bank_account_form',
    events: {
        'change select[name="country"]': '_onCountryChange',
    },

    start() {
        const self = this;

        this.$swiftInput = $('input.js-select2-swift');
        this.stateEl = this.el.querySelector('select[name="state"]');
        this.stateContainerEl = this.el.querySelector('label[for="state"]').parentElement;
        this.countryEl = this.el.querySelector('select[name="country"]');
        this.stateOptionEls = this.el.querySelectorAll('select[name="state"] > option');
        this.countrySpecificFields = this.el.querySelectorAll('.o_country_specific_bank_field');

        this._setupRequiredSelect2();
        this._onCountryChange();

        this.$swiftInput.select2({
            minimumInputLength: 4,
            maximumInputLength: 11,
            createSearchChoicePosition: 'bottom',

            formatNoMatches: function (_term) {
                return _t('Please specify a SWIFT/BIC code, up to 11 alphanumeric characters are allowed.');
            },

            // allow creating new item
            createSearchChoice: function (term) {
                // up to 11 alphanumeric characters, keep in sync with _sanity_check_bank_account()
                if (! term.match(/^[a-z0-9]+$/i) || term.length > 11) {
                    return null;
                }
                return { id: term, text: `Create '${term}'` };
            },

            ajax: {
                url: '/my/bank_account/get_banks',
                dataType: 'json',

                data: function (term) {
                    return {
                        bic: term,
                    };
                },

                processResults: function (data) {
                    return {
                        results: data.map(bank => {
                            return {
                                ...bank,
                                text: bank.bic,
                                id: bank.bic,  // "id" is what select2 uses as the "value" for the <option>
                            }
                        })
                    }
                }
            }
        }).on('select2-selecting', function (e) {
            // pre-populate all the res.banks fields
            // e.choice contains the selected result from processResults()
            for (let field in e.choice) {
                const value = e.choice[field];
                const input = self.el.querySelector(`input[name="${field}"], select[name="${field}"]`);
                if (input) {
                    input.value = value || '';
                }
            }
            self._onCountryChange(! e.choice.state);
        });
    },

    _setupRequiredSelect2() {
        // The name="bic" <input> is required in the DOM, but it's not handled well by select2. Saving the form when
        // nothing is set doesn't focus the widget, and the default browser popups don't show. This method adds invalid
        // listeners for each required input, opens the select2 widget when it's empty, and ignores all other invalid
        // fields to avoid focus immediately being moved elsewhere.
        this.el.querySelectorAll(":required").forEach(el => {
            el.addEventListener("invalid", event => {
                if (! this.$swiftInput.val()) {
                    event.preventDefault();
                    if (event.target === this.$swiftInput[0]) {
                        this.$swiftInput.select2("open");
                    }
                }
            });
        });
    },

    _setVisibilityStates(selectedCountry, setFirstState) {
        let countryHasStates = false;

        this.stateOptionEls.forEach(option => {
            if (selectedCountry === option.getAttribute('country')) {
                option.style.display = 'block';
                if (setFirstState && ! countryHasStates) {
                    this.stateEl.value = option.value;
                }
                countryHasStates = true;
            } else {
                option.style.display = 'none';
            }
        });

        this.stateEl.disabled = ! countryHasStates; // disable so it's not POSTed
        this.stateContainerEl.style.display = countryHasStates ? 'block' : 'none';
    },

    _setVisibilityCountrySpecificFields(selectedCountry) {
        this.countrySpecificFields.forEach(field => {
            const forCountry = field.getAttribute('data-country-id');
            field.disabled = forCountry && forCountry !== selectedCountry; // disable so it's not POSTed
            field.parentElement.style.display = field.disabled ? 'none' : 'block';
        });
    },

    _onCountryChange(setFirstState) {
        const selectedCountry = this.countryEl.value;
        this._setVisibilityStates(selectedCountry, setFirstState);
        this._setVisibilityCountrySpecificFields(selectedCountry);
    },
});

PublicWidget.registry.PurchaseDatePicker = PurchaseBankAccount;
