import { CustomerAddress } from "@portal/interactions/address";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();
        this.isSaCompany = this.countryCode === "SA";
        patchDynamicContent(this.dynamicContent, {
            'select[name="l10n_sa_edi_additional_identification_scheme"]': { "t-on-change": this._onChangeL10nSaScheme.bind(this) },
        });
        if (this.isSaCompany) {
            this.l10n_sa_edi_building_number = this.addressForm.l10n_sa_edi_building_number;
            this.l10n_sa_edi_plot_identification = this.addressForm.l10n_sa_edi_plot_identification;
            this.l10n_sa_edi_additional_identification_scheme = this.addressForm.l10n_sa_edi_additional_identification_scheme;
            this.l10n_sa_edi_additional_identification_number = this.addressForm.l10n_sa_edi_additional_identification_number;
            this._onChangeCountry()
            this._onChangeL10nSaScheme()
        }
    },

    async _setReadOnly(name) {
        this.addressForm[name].readOnly = true;
    },

    async _setEditable(name) {
        this.addressForm[name].readOnly = false;
    },

    async _onChangeCountry(init=false) {
        await this.waitFor(super._onChangeCountry(...arguments));
        if (!this.isSaCompany) {return;}

        if (this._getSelectedCountryCode() === "SA") {
            this._showInput("l10n_sa_edi_building_number");
            this._showInput("l10n_sa_edi_plot_identification");
            this._showInput("l10n_sa_edi_additional_identification_scheme");
            this._showInput("l10n_sa_edi_additional_identification_number");
        } else {
            this._hideInput("l10n_sa_edi_building_number");
            this._hideInput("l10n_sa_edi_plot_identification");
            this._hideInput("l10n_sa_edi_additional_identification_scheme");
            this._hideInput("l10n_sa_edi_additional_identification_number");
        }
    },

    async _onChangeL10nSaScheme() {
        const scheme = this.addressForm.l10n_sa_edi_additional_identification_scheme.value
        if (scheme === "TIN") {
            this.addressForm.l10n_sa_edi_additional_identification_number.value = ""
            this._setReadOnly("l10n_sa_edi_additional_identification_number")
        }
        else {
            this._setEditable("l10n_sa_edi_additional_identification_number")
        }
    },
});

