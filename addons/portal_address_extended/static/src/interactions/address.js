import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { CustomerAddress } from '@portal/interactions/address';
import { rpc } from '@web/core/network/rpc';


patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'select[name="city_id"]': { 't-on-change': this.onChangeCity.bind(this) },
            'select[name="state_id"]': { 't-on-change': this.onChangeState.bind(this) },
        });
        this.elementState = this.addressForm.state_id;
        this.elementCities = this.addressForm.city_id;
        this.countryEnforceCities = this.addressForm['enforce_cities'].value === "True";
    },

    _changeOption(selectElement, choices) {
        selectElement.options.length = 1;
        if (choices.length) {
            choices.forEach((item) => {
                const option = new Option(item[1], item[0]);
                selectElement.appendChild(option);
            });
        }
    },

    async onChangeCity() {},

    async onChangeState() {
        await this.waitFor(super.onChangeState());
        if (!this.countryEnforceCities || !this._getSelectedCountryEnforceCities(
            )) return;

        const stateId = this.elementState.value;
        let choices = [];
        if (stateId)  {
            const data = await this.waitFor(rpc(`/my/address/state_info/${stateId}`, {}));
            choices = data.cities;
        }
        this._changeOption(this.elementCities, choices);
    },

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if(!this.countryEnforceCities) return;

        if (this._getSelectedCountryEnforceCities()) {
            const cityInput = this.addressForm.city;
            cityInput.value = '';
            this._hideInput('city');
            this._hideInput('street');
            this._showInput('city_id');
            this._showInput('street_name');
            this._showInput('street_number');
            this._showInput('street_number2');

        } else {
            this._hideInput('city_id');
            this._hideInput('street_name');
            this._hideInput('street_number');
            this._hideInput('street_number2');
            this._showInput('city');
            this._showInput('street');
            this.elementCities.value = '';
        }
    },

    _getSelectedCountryEnforceCities() {
        const country = this.addressForm.country_id;
        return country.value ? country.selectedOptions[0].getAttribute('enforce-cities') : false;
    }
});
