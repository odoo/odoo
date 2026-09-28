import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { rpc } from "@web/core/network/rpc";
import { CustomerAddress } from "@portal/interactions/address";

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        patchDynamicContent(this.dynamicContent, {
            "select[name='l10n_cr_district_id']": { "t-on-change": this.onChangeL10nCrDistrict.bind(this) },
        });
    },

    async onChangeCountry() {
        const data = await super.onChangeCountry();
        if (this._getSelectedCountryCode() === "CR") {
            this._getInputDiv(this._getCityField()).after(this._getInputDiv("l10n_cr_district_id"));
            await this._l10nCrLoadDistricts();
        }
        return data;
    },

    async onChangeState() {
        const data = await super.onChangeState();
        if (this._getSelectedCountryCode() === "CR") {
            await this._l10nCrLoadDistricts();
        }
        return data;
    },

    async onChangeCity() {
        await super.onChangeCity();
        if (this._getSelectedCountryCode() === "CR") {
            await this._l10nCrLoadDistricts();
        }
    },

    async onChangeL10nCrDistrict() {
        const district = this.addressForm.l10n_cr_district_id.selectedOptions[0];
        const cityId = district?.dataset.cityId;
        if (!cityId || this.addressForm.city_id.value === cityId) {
            return;
        }
        if (this.addressForm.state_id.value !== district.dataset.stateId) {
            this.addressForm.state_id.value = district.dataset.stateId;
            await super.onChangeState();
        }
        this.addressForm.city_id.value = cityId;
        await this.onChangeCity();
    },

    async _l10nCrLoadDistricts() {
        const districtId = this.addressForm.l10n_cr_district_id.value;
        const districts = await this.waitFor(
            rpc("/my/address/l10n_cr_districts", {
                city_id: parseInt(this.addressForm.city_id?.value) || null,
                state_id: parseInt(this.addressForm.state_id.value) || null,
            })
        );
        this._setFieldChoices("l10n_cr_district_id", districts);
        this.addressForm.l10n_cr_district_id.value = districtId;
    },
});
