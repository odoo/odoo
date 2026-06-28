import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (this._getSelectedCountryCode() === 'MA') {
            this._showInput('ma_ice');
        } else if (this.addressForm.ma_ice) {
            this.addressForm.ma_ice.value = '';
            this._hideInput('ma_ice');
        }
    }
});
