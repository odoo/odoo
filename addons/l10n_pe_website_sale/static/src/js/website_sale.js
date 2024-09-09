/** @odoo-module **/
import {WebsiteSale} from "@website_sale/js/website_sale";

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
