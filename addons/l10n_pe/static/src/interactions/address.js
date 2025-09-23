import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        this.isPeruvianCompany = this.countryCode === 'PE';
        if (this.isPeruvianCompany) {
            this.elementDistricts = this.addressForm.l10n_pe_district;
        }
    },

    async onChangeCity() {
        await super.onChangeCity();
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
            this._showInput('l10n_pe_district');
        } else {
            this._hideInput('l10n_pe_district');
            this.elementDistricts.value = '';
        }
    },
});
