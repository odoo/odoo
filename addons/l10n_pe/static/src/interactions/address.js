/** @odoo-module native */
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { rpc } from "@web/core/network";
import { CustomerAddress } from "@portal/interactions/address";
import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("portal.address.pe");

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'select[name="city_id"]': { "t-on-change": this.onChangeCity.bind(this) },
        });

        this.isPeruvianCompany = this.countryCode === "PE";
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
                const option = new Option(item[1], item[0]);
                option.setAttribute("data-code", item[2]);
                selectElement.appendChild(option);
            });
        }
    },

    async onChangeState() {
        const parentChange = super.onChangeState(...arguments);
        if (!this.isPeruvianCompany || this._getSelectedCountryCode() !== "PE") {
            return await this.waitFor(parentChange);
        }

        const request = (this.peruvianStateRequest = Symbol());
        const countryRequest = this.peruvianCountryRequest;
        const stateId = this.elementState.value;
        this._changeOption(this.elementCities, []);
        this._changeOption(this.elementDistricts, []);
        await this.waitFor(parentChange);
        let choices = [];
        if (stateId) {
            const data = await this.waitFor(rpc(`/portal/state_infos/${stateId}`, {}));
            choices = data.cities;
        }
        if (
            request !== this.peruvianStateRequest ||
            countryRequest !== this.peruvianCountryRequest ||
            stateId !== this.elementState.value ||
            this._getSelectedCountryCode() !== "PE"
        ) {
            log.logic("discard stale state response", { stateId });
            return;
        }
        log.logic("apply state cities", { stateId });
        this._changeOption(this.elementCities, choices);
    },

    async onChangeCity() {
        if (!this.isPeruvianCompany || this._getSelectedCountryCode() !== "PE") return;

        const request = (this.peruvianCityRequest = Symbol());
        const countryRequest = this.peruvianCountryRequest;
        const stateRequest = this.peruvianStateRequest;
        const cityId = this.elementCities.value;
        this._changeOption(this.elementDistricts, []);
        let choices = [];
        if (cityId) {
            const data = await this.waitFor(rpc(`/portal/city_infos/${cityId}`, {}));
            choices = data.districts;
        }
        if (
            request !== this.peruvianCityRequest ||
            countryRequest !== this.peruvianCountryRequest ||
            stateRequest !== this.peruvianStateRequest ||
            cityId !== this.elementCities.value ||
            this._getSelectedCountryCode() !== "PE"
        ) {
            log.logic("discard stale city response", { cityId });
            return;
        }
        log.logic("apply city districts", { cityId });
        this._changeOption(this.elementDistricts, choices);
    },

    async _onChangeCountry(init = false) {
        const request = (this.peruvianCountryRequest = Symbol());
        const countryId = this.addressForm.country_id.value;
        if (this.isPeruvianCompany && !init) {
            this._changeOption(this.elementCities, []);
            this._changeOption(this.elementDistricts, []);
        }
        await this.waitFor(super._onChangeCountry(...arguments));
        if (!this.isPeruvianCompany) return;
        if (
            request !== this.peruvianCountryRequest ||
            countryId !== this.addressForm.country_id.value
        ) {
            log.logic("discard stale country extension", { countryId });
            return;
        }

        if (this._getSelectedCountryCode() === "PE") {
            const cityInput = this.addressForm.city;
            if (cityInput.value) {
                cityInput.value = "";
            }
            this._hideInput("city");
            this._showInput("city_id");
            this._showInput("l10n_pe_district");
        } else {
            this._hideInput("city_id");
            this._hideInput("l10n_pe_district");
            this._showInput("city");
            this.elementCities.value = "";
            this.elementDistricts.value = "";
        }
    },
});
