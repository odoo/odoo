import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class EditInvoicingInfo extends Interaction {
    static selector = ".o_l10n_tw_edi_invoicing_info";
    dynamicContent = {
        "#l10n_tw_edi_is_donate": {
            "t-on-change": this.onChangeDonateCheckbox,
        },
        "#l10n_tw_edi_carrier_type": {
            "t-on-change": this.onChangeCarrierType,
            "t-att-disabled": () => this.carrierTypeDisabled,
        },
        "#l10n_tw_edi_carrier_number": {
            "t-on-input": this.onInputCarrierNumber,
            "t-att-readonly": () => this.carrierNumberReadonly,
            "t-att-placeholder": () => this.carrierNumberPlaceholder,
        },
        "#l10n_tw_edi_carrier_number_2": {
            "t-att-placeholder": () => this.carrierNumberPlaceholder,
        },
        "#l10n_tw_edi_love_code": {
            "t-on-input": this.onInputLoveCode,
            "t-att-readonly": () => this.loveCodeReadonly,
        },
        "#validate_carrier_number": {
            "t-on-click": this.debounced(this.onClickValidateCarrierNumber, 500),
            "t-att-disabled": () => this.validateCarrierNumberDisabled,
            "t-att-class": () => ({
                "d-none": !this.showValidateCarrierNumber,
            }),
        },
        "#validate_love_code": {
            "t-on-click": this.debounced(this.onClickValidateLoveCode, 500),
            "t-att-disabled": () => this.validateLoveCodeDisabled,
            "t-att-class": () => ({
                "d-none": !this.showValidateLoveCode,
            }),
        },
        "#reenter_carrier_number": {
            "t-on-click": () => this.setCarrierNumberValidity(false),
            "t-att-class": () => ({
                "d-none": !this.showReenterCarrierNumber,
            }),
        },
        "#reenter_love_code": {
            "t-on-click": () => this.setLoveCodeValidity(false),
            "t-att-class": () => ({
                "d-none": !this.showReenterLoveCode,
            }),
        },
        "#ecpay_invoice_love_code": {
            "t-att-class": () => ({
                "d-none": !this.showLoveCode,
            }),
        },
        "#ecpay_carrier_type_group": {
            "t-att-class": () => ({
                "d-none": !this.showCarrierType,
            }),
        },
        "#ecpay_invoice_carrier_number": {
            "t-att-class": () => ({
                "d-none": !this.showCarrier,
            }),
        },
        "#ecpay_invoice_carrier_number_2": {
            "t-att-class": () => ({
                "d-none": !this.showCarrier2,
            }),
        },
    };

    setup() {
        // Visibility
        this.showLoveCode = false;
        this.showCarrierType = false;
        this.showCarrier = false;
        this.showCarrier2 = false;
        this.showValidateLoveCode = false;
        this.showValidateCarrierNumber = false;
        this.showReenterCarrierNumber = false;
        this.showReenterLoveCode = false;

        // Attributes
        this.carrierTypeDisabled = false;
        this.carrierNumberReadonly = false;
        this.loveCodeReadonly = false;
        this.validateCarrierNumberDisabled = false;
        this.validateLoveCodeDisabled = false;
        this.carrierNumberPlaceholder = "";
        this.carrierNumberPlaceholder2 = "";

        this.validCarrierNumber = false;
        this.validLoveCode = false;

        const isElementVisible = (id) => !document.getElementById(id).classList.contains("d-none");

        if (document.getElementById("ecpay_invoice_method")) {
            this.showLoveCode = isElementVisible("ecpay_invoice_love_code");
            this.showCarrierType = isElementVisible("ecpay_carrier_type_group");
            this.showCarrier = isElementVisible("ecpay_invoice_carrier_number");
            this.showCarrier2 = isElementVisible("ecpay_invoice_carrier_number_2");
            this.showValidateLoveCode = isElementVisible("ecpay_invoice_love_code");
            if (document.getElementById("l10n_tw_edi_carrier_type").value === "3") {
                this.showValidateCarrierNumber = true;
            }
        }
    }

    getTokenInfo() {
        const form = document.getElementById("form_l10n_tw_invoicing_info");
        const saleOrderId = form.getAttribute("date-order-id");
        const accessToken = form.getAttribute("data-access-token");
        return { saleOrderId, accessToken };
    }

    onChangeDonateCheckbox(ev) {
        const isChecked = ev.target.checked;
        this.showLoveCode = isChecked;
        this.showValidateLoveCode = isChecked && !this.validLoveCode;
        this.showReenterLoveCode = isChecked && this.validLoveCode;
        const loveCodeInput = document.getElementById("l10n_tw_edi_love_code");
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.validateLoveCodeDisabled = !re.test(loveCodeInput.value);
        this.showCarrierType = !isChecked;
    }

    onChangeCarrierType(ev) {
        const carrierType = ev.target.value;
        const carrierNumberField = document.getElementById("l10n_tw_edi_carrier_number");
        if (carrierType === "2") {
            this.carrierNumberPlaceholder = _t("Example: TP03000001234567");
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
        } else if (carrierType === "3") {
            this.carrierNumberPlaceholder = _t("Example: /ABCD123");
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = !this.validCarrierNumber;
            this.showReenterCarrierNumber = this.validCarrierNumber;
            const re = /^\/[0-9a-zA-Z+-.]{7}$/;
            this.validateCarrierNumberDisabled = !re.test(carrierNumberField.value);
        } else if (["4", "5"].includes(carrierType)) {
            this.carrierNumberPlaceholder = _t("Card hidden code");
            this.carrierNumberPlaceholder2 = _t("Card visible code");
            this.showCarrier = true;
            this.showCarrier2 = true;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
        } else {
            this.showCarrier = false;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
        }
        this.validCarrierNumber = false;
    }

    onInputCarrierNumber(ev) {
        const carrierType = document.getElementById("l10n_tw_edi_carrier_type").value;
        if (carrierType === "2") {
            const re = /^[A-Z]{2}[0-9]{14}$/;
            this.validCarrierNumber = re.test(ev.target.value);
        } else if (carrierType === "3") {
            const re = /^\/[0-9a-zA-Z+-.]{7}$/;
            this.validateCarrierNumberDisabled = !re.test(ev.target.value);
        }
    }

    onInputLoveCode(ev) {
        this.validLoveCode = false;
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.validateLoveCodeDisabled = !re.test(ev.target.value);
    }

    async onClickValidateCarrierNumber() {
        try {
            const { saleOrderId, accessToken } = this.getTokenInfo();
            const result = await this.waitFor(
                rpc("/payment/ecpay/check_mobile_barcode/" + saleOrderId, {
                    access_token: accessToken,
                    carrier_number: document.getElementById("l10n_tw_edi_carrier_number").value,
                })
            );
            if (result) {
                this.setCarrierNumberValidity(true);
            } else {
                this.services.dialog.add(WarningDialog, {
                    title: _t("Error"),
                    message: _t("Carrier number is invalid"),
                });
            }
        } catch (error) {
            this.services.dialog.add(WarningDialog, {
                title: _t("ECpay Error"),
                message: error.data.message,
            });
        }
    }

    async onClickValidateLoveCode() {
        try {
            const { saleOrderId, accessToken } = this.getTokenInfo();
            const result = await this.waitFor(
                rpc("/payment/ecpay/check_love_code/" + saleOrderId, {
                    access_token: accessToken,
                    love_code: this.el.querySelector("#l10n_tw_edi_love_code").value,
                })
            );

            if (result) {
                this.setLoveCodeValidity(true);
            } else {
                this.services.dialog.add(WarningDialog, {
                    title: _t("Error"),
                    message: _t("Love code is invalid"),
                });
            }
        } catch (error) {
            this.services.dialog.add(WarningDialog, {
                title: _t("ECpay Error"),
                message: error.data.message,
            });
        }
    }

    setCarrierNumberValidity(validity) {
        this.validCarrierNumber = validity;
        this.showValidateCarrierNumber = !validity;
        this.showReenterCarrierNumber = validity;
        this.carrierTypeDisabled = validity;
        this.carrierNumberReadonly = validity;
    }

    setLoveCodeValidity(validity) {
        this.validLoveCode = validity;
        this.showValidateLoveCode = !validity;
        this.showReenterLoveCode = validity;
        this.loveCodeReadonly = validity;
    }
}

registry
    .category("public.interactions")
    .add("l10n_tw_edi_ecpay_website_sale.edit_invoicing_info", EditInvoicingInfo);
