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
<<<<<<< ce6be20933c916b6e236d607cfef8251a20feec4
        this._super.apply(this, arguments);

        this.elementCountry = this.addressForm.country_id;
        this.isPeruvianCompany = this.countryCode === 'PE';
||||||| 20bb44130d6ce1924b235fe3aee8ec7ffad01cbd
        this.elementCities = document.querySelector("select[name='city_id']");
        this.elementDistricts = document.querySelector("select[name='l10n_pe_district']");
        this.cityBlock = document.querySelector(".div_city");
        this.autoFormat = document.querySelector(".checkout_autoformat");
        this.elementState = document.querySelector("select[name='state_id']");
        this.elemenCountry = document.querySelector("select[name='country_id']");
        this.isPeruvianCompany = this.elemenCountry?.dataset.company_country_code === 'PE';
        return this._super.apply(this, arguments);
    },
    _changeOption: function (selectCheck, rpcRoute, place, selectElement) {
        if (!selectCheck) {
            return;
        }
        return this.rpc(rpcRoute, {
        }).then((data) => {
            if (this.isPeruvianCompany) {
                if (data[place]?.length) {
                    selectElement.innerHTML = "";
                    data[place].forEach((item) => {
                        let opt = document.createElement("option");
                        opt.textContent = item[1];
                        opt.value = item[0];
                        opt.setAttribute("data-code", item[2]);
                        selectElement.appendChild(opt);
                    });
                    selectElement.parentElement.style.display = "block";
                } else {
                    selectElement.value = "";
                    selectElement.parentElement.style.display = "none";
                }
            }
        });
    },
    _onChangeState: function (ev) {
        return this._super.apply(this, arguments).then(() => {
            let selectedCountry = this.elemenCountry.options[this.elemenCountry.selectedIndex].getAttribute("code");
            if (this.isPeruvianCompany && selectedCountry === "PE") {
                if (this.elementState.value === "" && this.elemenCountry.value !== '') {
                    this.elementState.options[1].selected = true;
                }
                const state = this.elementState.value;
                const rpcRoute = `/shop/state_infos/${state}`;
                return this.autoFormat.length
                    ? this._changeOption(state, rpcRoute, "cities", this.elementCities).then(() => this._onChangeCity())
                    : undefined;
            }
        });
    },
    _onChangeCity: function () {
=======
        this.elementCities = document.querySelector("select[name='city_id']");
        this.elementDistricts = document.querySelector("select[name='l10n_pe_district']");
        this.cityBlock = document.querySelector(".div_city");
        this.autoFormat = document.querySelector(".checkout_autoformat");
        this.elementState = document.querySelector("select[name='state_id']");
        this.elemenCountry = document.querySelector("select[name='country_id']");
        this.isPeruvianCompany = this.elemenCountry?.dataset.company_country_code === 'PE';
        return this._super.apply(this, arguments);
    },
    _changeOption: function (selectCheck, rpcRoute, place, selectElement) {
        if (!selectCheck) {
            return;
        }
        return this.rpc(rpcRoute, {
        }).then((data) => {
            if (this.isPeruvianCompany) {
                if (data[place]?.length) {
                    let previousValue = selectElement.value;
                    selectElement.innerHTML = "";
                    data[place].forEach((item) => {
                        let opt = document.createElement("option");
                        opt.textContent = item[1];
                        opt.value = item[0];
                        opt.setAttribute("data-code", item[2]);
                        selectElement.appendChild(opt);
                    });
                if ([...selectElement.options].some(opt => opt.value === previousValue)) {
                    selectElement.value = previousValue;
                }
                    selectElement.parentElement.style.display = "block";
                } else {
                    selectElement.value = "";
                    selectElement.parentElement.style.display = "none";
                }
            }
        });
    },
    _onChangeState: function (ev) {
        return this._super.apply(this, arguments).then(() => {
            let selectedCountry = this.elemenCountry.options[this.elemenCountry.selectedIndex].getAttribute("code");
            if (this.isPeruvianCompany && selectedCountry === "PE") {
                if (this.elementState.value === "" && this.elemenCountry.value !== '') {
                    this.elementState.options[1].selected = true;
                }
                const state = this.elementState.value;
                const rpcRoute = `/shop/state_infos/${state}`;
                return this.autoFormat.length
                    ? this._changeOption(state, rpcRoute, "cities", this.elementCities).then(() => this._onChangeCity())
                    : undefined;
            }
        });
    },
    _onChangeCity: function () {
>>>>>>> e061ae07d1a89091865059bfecc03b007d99f113
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
