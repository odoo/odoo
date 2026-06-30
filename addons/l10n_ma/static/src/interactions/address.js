import { patch } from '@web/core/utils/patch';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {
    _getAddressFields() {
        const addressFields = super._getAddressFields();
        if (this._getSelectedCountryCode() === "MA") {
            addressFields.add("ma_ice");
        }
        return addressFields;
    },
});
