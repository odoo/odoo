/** @odoo-module **/

import websiteSaleAddress from "@website_sale/js/address";
import { rpc } from "@web/core/network/rpc";

websiteSaleAddress.include({
    events: Object.assign(
        {},
        websiteSaleAddress.prototype.events,
        {
            "change select[name='city_id']": "_onChangeCity",
        }
    ),

    start: function () {
        this._super.apply(this, arguments);

        this.elementCountry = this.addressForm.country_id;
        this.isPeruvianCompany = this.countryCode === 'PE';
        if (this.isPeruvianCompany) {
            this.elementState = this.addressForm.state_id;
            this.elementCities = this.addressForm.city_id;
            this.elementDistricts = this.addressForm.l10n_pe_district;
        }
    },

    _changeOption(selectElement, choices) {
        // empty existing options, only keep the placeholder.
        selectElement.options.length = 1;
        if (choices.length) {
            choices.forEach((item) => {
                let option = new Option(item[1], item[0]);
                option.setAttribute('data-code', item[2]);
                selectElement.appendChild(option);
            });
        }
    },

    async _onChangeState() {
        await this._super(...arguments);
        let selectedCountry = this.elementCountry.value ?
            this.elementCountry.selectedOptions[0].getAttribute('code') : '';
        if (this.isPeruvianCompany && selectedCountry === "PE") {
            const stateId = this.elementState.value;
            let choices = [];
            if (stateId)  {
                const data = await rpc(`/shop/state_infos/${stateId}`, {});
                choices = data.cities;
            }
            this._changeOption(this.elementCities, choices);
            // reset districts input as well
            this._onChangeCity();
        }
    },

    async _onChangeCity() {
        if (this.isPeruvianCompany) {
            const cityId = this.elementCities.value;
            let choices = [];
            if (cityId) {
                const data = await rpc(`/shop/city_infos/${cityId}`, {});
                choices = data.districts;
            }
            this._changeOption(this.elementDistricts, choices);
        }
    },

    async _changeCountry(init=false) {
        await this._super(...arguments);
        if (this.isPeruvianCompany) {
            let selectedCountry = this.elementCountry.value ?
                this.elementCountry.selectedOptions[0].getAttribute('code') : '';
            if (selectedCountry == 'PE') {
                let cityInput = this.addressForm.city;
                if (cityInput.value) {
                    cityInput.value = '';
                }
                this._hideInput('city');
                this._showInput('city_id');
                this._showInput('l10n_pe_district');
            } else {
                this._hideInput('city_id');
                this._hideInput('l10n_pe_district');
                this._showInput('city');
                this.elementCities.value = '';
                this.elementDistricts.value = '';
            }
        }
    },
});
