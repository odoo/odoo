import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.websiteSaleAddressExtended = publicWidget.registry.websiteSaleAddress.extend({
    events: {
        "input #o_vat": "_onChangeVat",
        'change select[name="country_id"]': "_onChangeCountry",
    },

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this._onChangeVat = debounce(this._onChangeVat.bind(this), 400);
        this.l10n_in_gst_treatment = document.querySelector(
            "div[name='l10n_in_gst_treatment_container']"
        );
        this._gst_treatment = this.addressForm.l10n_in_gst_treatment?.value ?? "";
        this._invalid_vat = false;
    },

    _onChangeVat(ev) {
        if (this.countryCode === "IN") {
            this._setL10nInGstTreatment();
        }
    },

    /**
     * @override
     */
    async _changeCountry(init = false) {
        this._super();
        if (this.countryCode === "IN") {
            this._setL10nInGstTreatment();
        }
    },

    _setL10nInGstTreatment() {
        const selectedCountry =
            this.addressForm.country_id.options[
                this.addressForm.country_id.selectedIndex
            ].getAttribute("code");
        const form_gst_treatment = this.addressForm.l10n_in_gst_treatment;
        const form_vat = this.addressForm.vat;

        if (this.countryCode === "IN" && this.l10n_in_gst_treatment) {
            this.l10n_in_gst_treatment.style.display = "block";
            if (selectedCountry && selectedCountry !== "IN") {
                this._gst_treatment = !this._invalid_vat
                    ? form_gst_treatment.value
                    : this._gst_treatment;
                this._invalid_vat = true;
                form_gst_treatment.value = "overseas";
                form_gst_treatment.disabled = true;
            } else {
                const isValidVat = this._validateVAT(form_vat?.value?.trim() ?? "");
                form_gst_treatment.disabled = !isValidVat;
                this._gst_treatment = !this._invalid_vat
                    ? form_gst_treatment.value
                    : this._gst_treatment;
                form_gst_treatment.value = isValidVat ? this._gst_treatment : "consumer";
                this._invalid_vat = !isValidVat;
            }
        } else if (this.l10n_in_gst_treatment) {
            this.l10n_in_gst_treatment.style.display = "none";
        }
    },

    _validateVAT(vat) {
        if (vat && vat.length === 15) {
            const allGstinRe = [
                /^[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[Zz1-9A-Ja-j]{1}[0-9a-zA-Z]{1}$/, // Normal, Composite, Casual GSTIN
                /^[0-9]{4}[A-Z]{3}[0-9]{5}[UO]{1}[N][A-Z0-9]{1}$/, // UN/ON Body GSTIN
                /^[0-9]{4}[a-zA-Z]{3}[0-9]{5}[N][R][0-9a-zA-Z]{1}$/, // NRI GSTIN
                /^[0-9]{2}[a-zA-Z]{4}[a-zA-Z0-9]{1}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[DK]{1}[0-9a-zA-Z]{1}$/, // TDS GSTIN
                /^[0-9]{2}[a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9A-Za-z]{1}[C]{1}[0-9a-zA-Z]{1}$/, // TCS GSTIN
            ];
            return allGstinRe.some((rx) => rx.test(vat));
        }
        return false;
    },
});
