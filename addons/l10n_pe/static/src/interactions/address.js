import { patch } from '@web/core/utils/patch';
import { rpc } from '@web/core/network/rpc';
import { CustomerAddress } from '@portal/interactions/address';

patch(CustomerAddress.prototype, {

    _getAddressFields() {
        const addressFields = super._getAddressFields();
        if (this._getSelectedCountryCode() === "PE") {
            addressFields.add("l10n_pe_district");
        }
        return addressFields;
    },

    async onChangeCity() {
        await super.onChangeCity();
        if (this.countryCode !== "PE" || this._getSelectedCountryCode() !== "PE") return;

        const cityId = parseInt(this.addressForm.city_id.value);
        let data = {};
        if (cityId)  {
            data = await this.waitFor(rpc(`/my/address/city_info/${cityId}`, {}));
        }
        this._setFieldChoices("l10n_pe_district", data.districts || []);
    },

});
