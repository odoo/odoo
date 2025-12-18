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
        this.onChangeType();
    },

    onChangeType(ev = null) {
        const radio = this.el.querySelector('input[name="company_type"]:checked');

        if (!radio) {
            return;
        }

        if (ev) {
            const l10nClassificationNumberLabel = this.el.querySelector(
                'label[for="l10n_my_identification_number"]'
            );

            if (l10nClassificationNumberLabel) {
                l10nClassificationNumberLabel.textContent =
                    radio.value === "company"
                        ? "Business Registration Number"
                        : "Identification Number";
            }

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
    },

    async _onChangeCountry(init = false) {
        await super._onChangeCountry(init);

        if (!this.el.querySelector('input[name="l10n_my_edi_malaysian_tin"]')) {
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
});
