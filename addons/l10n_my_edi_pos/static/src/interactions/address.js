import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { patchDynamicContent } from "@web/public/utils";
import { CustomerAddress } from "@portal/interactions/address";

patch(CustomerAddress.prototype, {
    setup() {
        super.setup();

        patchDynamicContent(this.dynamicContent, {
            'input[name="company_type"]': {
                "t-on-change": this.onChangeType.bind(this),
            },
        });
    },

    start() {
        super.start();
        if (!this.el.querySelector('input[name="company_type"]:checked')) {
            return;
        }

        this._hideInput("parent_name");
        const applyValidation = (field_name, pattern, title) => {
            const field = this.el.querySelector(`input[name="${field_name}"]`);

            if (field) {
                field.pattern = pattern;
                field.title = _t(title);
            }
        };
        applyValidation("zip", "[0-9]+", "Zip code must contain only numbers");
        applyValidation(
            "phone",
            "\\+[1-9][0-9]{6,14}",
            "Phone Number must be in E.164 format (e.g. +60123456789)"
        );
        this.onChangeType();
    },

    _updateTinVisibility() {
        const radio = this.el.querySelector('input[name="company_type"]:checked');

        if (!radio || !this.el.querySelector('input[name="l10n_my_edi_malaysian_tin"]')) {
            return;
        }

        if (radio.value === "person") {
            this._showInput("l10n_my_edi_malaysian_tin");
            this._hideInput("vat");
            return;
        }

        if (this._getSelectedCountryCode() === "MY") {
            this._hideInput("l10n_my_edi_malaysian_tin");
            this._showInput("vat");
        } else {
            this._showInput("l10n_my_edi_malaysian_tin");
            this._hideInput("vat");
        }
    },

    onChangeType(ev = null) {
        const radio = this.el.querySelector('input[name="company_type"]:checked');

        if (!radio) {
            return;
        }

        const setLabel = (forAttr, companyText, individualText) => {
            const label = this.el.querySelector(`label[for="${forAttr}"]`);
            if (label) {
                label.textContent =
                    radio.value === "company" ? _t(companyText) : _t(individualText);
            }
        };

        setLabel("o_name", "Company Name", "Your Name");
        setLabel(
            "l10n_my_identification_number",
            "Business Registration Number",
            "Identification Number"
        );
        setLabel("o_vat", "TIN", "Malaysian TIN");

        if (ev) {
            const nameInput = this.el.querySelector('input[name="name"]');
            if (nameInput) {
                nameInput.value = "";
            }

            const errorBlock = this.el.querySelector(".o_portal_address_error");
            if (errorBlock) {
                errorBlock.style.display = "none";
            }
        }

        if (radio.value === "person") {
            this._hideInput("l10n_my_edi_industrial_classification");
            this._showInput("l10n_my_identification_type");
        } else {
            this._hideInput("l10n_my_identification_type");
            this._showInput("l10n_my_edi_industrial_classification");
        }

        this._updateTinVisibility();
    },

    async _onChangeCountry(init = false) {
        await super._onChangeCountry(init);
        this._updateTinVisibility();
    },
});
