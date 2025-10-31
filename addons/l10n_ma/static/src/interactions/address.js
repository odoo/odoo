import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (this._getSelectedCountryCode() === 'MA') {
            this._showInput('company_registry');
        } else if (this.addressForm.company_registry) {
            this.addressForm.company_registry.value = '';
            this._hideInput('company_registry');
        }
    }
});
