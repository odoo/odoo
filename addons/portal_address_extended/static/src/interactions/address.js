import { patch } from '@web/core/utils/patch';
import { patchDynamicContent } from '@web/public/utils';
import { CustomerAddress } from '@portal/interactions/address';
import { rpc } from '@web/core/network/rpc';


patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            'input[name="zip"]': { 't-on-input': this.onChangeZip.bind(this) },
            'select[name="city_id"]': { 't-on-change': this.onChangeCity.bind(this) },
        });
        this.elementState = this.addressForm.state_id;
        this.elementCities = this.addressForm.city_id;
    },

    /**
     * Overridable hook.
     */
    async onChangeZip() {},

    async onChangeCity() {},

    async onChangeState() {
        await this.waitFor(super.onChangeState());
        if (!this._getSelectedCountryEnforceCities()) return;

        const stateId = this.elementState.value;
        let choices = [];
        if (stateId)  {
            const data = await this.waitFor(rpc(`/my/address/state_info/${stateId}`, {}));
            choices = data.cities;
        }
        this._changeOption(this.elementCities, choices);
    },

    async _onChangeCountry(init=false) {
        const data = await this.waitFor(super._onChangeCountry(...arguments));

        let choices = [];
        if (this._getSelectedCountryEnforceCities()) {
            const cityInput = this.addressForm.city;
            cityInput.value = '';
            this._hideInput('city');
            this._showInput('city_id');
            choices = data.cities || [];
        } else {
            this._hideInput('city_id');
            this._showInput('city');
        }
        this._changeOption(this.elementCities, choices);
    },

    _changeOption(selectElement, choices) {
        selectElement.options.length = 1;
        if (choices.length) {
            choices.forEach((choice) => {
                const option = new Option(choice.name, choice.id);
                Object.keys(choice).forEach((key) => {
                    if (!['name', 'id'].includes(key) && choice[key]) {
                        option.dataset[key] = choice[key];
                    }
                });
                selectElement.appendChild(option);
            });
        }
    },

    _getSelectedCountryEnforceCities() {
        const country = this.addressForm.country_id;
        return country.value ? country.selectedOptions[0].getAttribute('enforce-cities') : false;
    }
});
