/** @odoo-module **/
import {WebsiteSale} from "@website_sale/js/website_sale";
import {KeepLast} from "@web/core/utils/concurrency";

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        "change select[name='city_id']": "_onChangeCity",
    }),
    start: function () {
        this.elementCities = document.querySelector("select[name='city_id']");
        this.elementDistricts = document.querySelector("select[name='l10n_pe_district']");
        this.cityBlock = document.querySelector(".div_city");
        this.autoFormat = document.querySelector(".checkout_autoformat");
        this.elementState = document.querySelector("select[name='state_id']");
        this.elemenCountry = document.querySelector("select[name='country_id']");
        this.isPeruvianCompany = this.elemenCountry?.dataset.company_country_code === 'PE';
        if (this.isPeruvianCompany) {
            const selectedCountryCode = this.elemenCountry.options[this.elemenCountry.selectedIndex]?.getAttribute("code");
            if (selectedCountryCode === "PE") {
                // Keep disabled until _changeOption's refresh
                this.elementCities.disabled = !!this.elementState.value;
                this.elementDistricts.disabled = !!this.elementCities.value;
            }
        }
        this.pendingOptionsFetches = {
            cities: new KeepLast(),
            districts: new KeepLast(),
        };
        return this._super.apply(this, arguments);
    },
    _changeOption: function (selectCheck, rpcRoute, place, selectElement) {
        if (!selectCheck) {
            return;
        }
        // Disabled while in flight to prevent race conditions
        selectElement.disabled = true;
        if (place === "cities") {
            this.elementDistricts.disabled = true;
        }

        return this.pendingOptionsFetches[place].add(this.rpc(rpcRoute, {})).then((data) => {
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
        }).finally(() => {
            selectElement.disabled = false;
            if (place === "cities") {
                this.elementDistricts.disabled = false;
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
        if (this.isPeruvianCompany) {
            const city = this.elementCities.value;
            const rpcRoute = `/shop/city_infos/${city}`;
            return this.autoFormat.length
                ? this._changeOption(city, rpcRoute, "districts", this.elementDistricts)
                : undefined;
        }
    },
    _onChangeCountry: function (ev) {
        return this._super.apply(this, arguments).then(() => {
            if (this.isPeruvianCompany) {
                let selectedCountry = ev.currentTarget.options[ev.currentTarget.selectedIndex].getAttribute("code");
                let cityInput = document.querySelector(".form-control[name='city']");
                if (selectedCountry == "PE") {
                    if (cityInput.value) {
                        cityInput.value = "";
                    }
                    this.cityBlock.classList.add("d-none");
                    return this._onChangeState().then(() => {
                        this._onChangeCity();
                    });
                } else {
                    this.cityBlock.querySelectorAll("input").forEach((input) => {
                        input.value = "";
                    });
                    this.cityBlock.classList.remove("d-none");
                    this.elementCities.value = "";
                    this.elementCities.parentElement.style.display = "none";
                    this.elementDistricts.value = "";
                    this.elementDistricts.parentElement.style.display = "none";
                }
            }
        });
    },
});
