import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (this._getSelectedCountryCode() === 'MA') {
            this._showInput('MA_ICE');
        } else if (this.addressForm['MA_ICE']) {
            this.addressForm['MA_ICE'].value = '';
            this._hideInput('MA_ICE');
        }
    }
});
