import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { rpc } from '@web/core/network/rpc';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'select[name="city_id"]': { 't-on-change': this.onChangeCity.bind(this) },
        });

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
                const option = new Option(item[1], item[0]);
                option.setAttribute('data-code', item[2]);
                selectElement.appendChild(option);
            });
        }
    },

    async onChangeState() {
        await this.waitFor(super.onChangeState());
        if (!this.isPeruvianCompany || this._getSelectedCountryCode() !== 'PE') return;

        const stateId = this.elementState.value;
        let choices = [];
        if (stateId)  {
            const data = await this.waitFor(rpc(`/portal/state_infos/${stateId}`, {}));
            choices = data.cities;
        }
        this._changeOption(this.elementCities, choices);
        // reset districts input as well
        await this.onChangeCity();
    },

    async onChangeCity() {
        if (!this.isPeruvianCompany || this._getSelectedCountryCode() !== 'PE') return;

        const cityId = this.elementCities.value;
        let choices = [];
        if (cityId) {
            const data = await this.waitFor(rpc(`/portal/city_infos/${cityId}`, {}));
            choices = data.districts;
        }
        this._changeOption(this.elementDistricts, choices);
    },

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (!this.isPeruvianCompany) return;

        if (this._getSelectedCountryCode() === 'PE') {
            const cityInput = this.addressForm.city;
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
    },
});
