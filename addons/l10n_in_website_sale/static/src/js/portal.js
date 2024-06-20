import publicWidget from "@web/legacy/js/public/public_widget";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.portalDetailsExtend = publicWidget.registry.portalDetails.extend({
    events: {
        'input input[name="vat"]': "_onChangeVat",
        'change select[name="country_id"]': "_onCountryChange",
    },

    start: function () {
        this._super.apply(this, arguments);

        this._onChangeVat = debounce(this._onChangeVat.bind(this), 400);
        this.countryCode = document.querySelector(
            'form[action="/my/account"]'
        ).dataset.companyCountryCode;
        this.elementCountry = this.el.querySelector("select[name='country_id']");
        this.l10n_in_gst_treatment = this.el.querySelector(
            "div[name='l10n_in_gst_treatment_container']"
        );
        this._gst_treatment =
            this.el.querySelector("select[name='l10n_in_gst_treatment']")?.value ?? "";
        this._invalid_vat = false;

        this._setL10nInGstTreatment();
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeVat(ev) {
        if (this.countryCode === "IN") {
            this._setL10nInGstTreatment();
        }
    },

    /**
     * @override
     */
    _onCountryChange: function () {
        if (this.countryCode === "IN") {
            this._setL10nInGstTreatment();
        }
        return this._super();
    },

    _setL10nInGstTreatment() {
        const selectedCountry =
            this.elementCountry.options[this.elementCountry.selectedIndex].getAttribute("code");
        const form_gst_treatment = this.el.querySelector("select[name='l10n_in_gst_treatment']");
        const form_vat = this.el.querySelector("input[name='vat']");

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
