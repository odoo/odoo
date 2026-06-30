/** @odoo-module **/
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.knowledgeBaseAutocomplete = publicWidget.Widget.extend({
    selector: ".o_l10n_tw_edi_invoicing_info",

    events: {
        "change #l10n_tw_edi_is_donate": "_onChangeDonateCheckbox",
        "change #l10n_tw_edi_carrier_type": "_onChangeCarrierType",
        "input #l10n_tw_edi_carrier_number": "_onInputCarrierNumber",
        "input #l10n_tw_edi_love_code": "_onInputLoveCode",
        "click #validate_carrier_number": "_onClickValidateCarrierNumber",
        "click #validate_love_code": "_onClickValidateLoveCode",
        "click #reenter_carrier_number": "_onClickReenterCarrierNumber",
        "click #reenter_love_code": "_onClickReenterLoveCode",
    },

    init: function () {
        this._super.apply(this, arguments);
        this._onClickValidateCarrierNumber = debounce(
            this._onClickValidateCarrierNumber.bind(this),
            500
        );
        this._onClickValidateLoveCode = debounce(this._onClickValidateLoveCode.bind(this), 500);
    },

    start: function () {
        if (document.querySelector("#ecpay_invoice_method")) {
            this.showLoveCode = !document
                .querySelector("#ecpay_invoice_love_code")
                .classList.contains("d-none");
            this.showCarrierType = !document
                .querySelector("#ecpay_carrier_type_group")
                .classList.contains("d-none");
            this.showCarrier = !document
                .querySelector("#ecpay_invoice_carrier_number")
                .classList.contains("d-none");
            this.showCarrier2 = !document
                .querySelector("#ecpay_invoice_carrier_number_2")
                .classList.contains("d-none");
            this.validCarrierNumber = false;
            this.validLoveCode = false;
            this.showValidateCarrierNumber = false;
            if (
                document.querySelector("#l10n_tw_edi_carrier_type").value === "3"
            ) {
                this.showValidateCarrierNumber = true;
                document.querySelector("#validate_carrier_number").classList.remove("d-none");
            }
            this.showValidateLoveCode = false;
            if (!document
                .querySelector("#ecpay_invoice_love_code")
                .classList.contains("d-none")) {
                this.showValidateLoveCode = true;
                document.querySelector("#validate_love_code").classList.remove("d-none");
            }
            this.showReenterCarrierNumber = false;
            this.showReenterLoveCode = false;
        }
        return this._super.apply(this, arguments);
    },

    getTokenInfo() {
        const form = document.getElementById("form_l10n_tw_invoicing_info");
        const saleOrderId = form.getAttribute("date-order-id");
        const accessToken = form.getAttribute("data-access-token");
        return { saleOrderId, accessToken };
    },

    showInvoiceItems() {
        const elementsToShow = new Map([
            ["#ecpay_invoice_love_code", this.showLoveCode],
            ["#ecpay_carrier_type_group", this.showCarrierType],
            ["#ecpay_invoice_carrier_number", this.showCarrier],
            ["#ecpay_invoice_carrier_number_2", this.showCarrier2],
            ["#validate_carrier_number", this.showValidateCarrierNumber],
            ["#validate_love_code", this.showValidateLoveCode],
            ["#reenter_carrier_number", this.showReenterCarrierNumber],
            ["#reenter_love_code", this.showReenterLoveCode],
        ]);

        elementsToShow.forEach((isShown, selector) => {
            this.el.querySelector(selector).classList.toggle("d-none", !isShown);
        });
    },

    _onChangeDonateCheckbox(ev) {
        const isChecked = ev.target.checked;
        this.showLoveCode = isChecked;
        this.showValidateLoveCode = isChecked && !this.validLoveCode;
        this.showReenterLoveCode = isChecked && this.validLoveCode;
        const loveCodeInput = this.el.querySelector("#l10n_tw_edi_love_code");
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.el.querySelector("#validate_love_code").disabled = !re.test(loveCodeInput.value);
        this.showCarrierType = !isChecked;
        this.showInvoiceItems();
    },

    _onChangeCarrierType(ev) {
        const carrierType = ev.target.value;
        const carrierNumberField = document.querySelector("#l10n_tw_edi_carrier_number")
        carrierNumberField.removeAttribute("readonly");
        if (carrierType === "2") {
            carrierNumberField.placeholder = _t(
                "Example: TP03000001234567"
            );
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
        } else if (carrierType === "3") {
            carrierNumberField.placeholder = _t(
                "Example: /ABCD123"
            );
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = !this.validCarrierNumber;
            this.showReenterCarrierNumber = this.validCarrierNumber;
            const re = /^\/[0-9a-zA-Z+-.]{7}$/;
            this.el.querySelector("#validate_carrier_number").disabled = !re.test(carrierNumberField.value);
        } else if (["4", "5"].includes(carrierType)) {
            carrierNumberField.placeholder = "";
            this.showCarrier = true;
            this.showCarrier2 = true;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
            carrierNumberField.placeholder =
                _t("Card hidden code");
            document.querySelector("#l10n_tw_edi_carrier_number_2").placeholder =
                _t("Card visible code");
        } else {
            this.showCarrier = false;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = false;
            this.showReenterCarrierNumber = false;
        }
        this.validCarrierNumber = false;
        this.showInvoiceItems();
    },

    _onInputCarrierNumber(ev) {
        const carrierType = this.el.querySelector("#l10n_tw_edi_carrier_type").value;
        if (carrierType === "2") {
            const re = /^[A-Z]{2}[0-9]{14}$/;
            this.validCarrierNumber = re.test(ev.target.value);
        } else if (carrierType === "3") {
            const re = /^\/[0-9a-zA-Z+-.]{7}$/;
            this.el.querySelector("#validate_carrier_number").disabled = !re.test(ev.target.value);
        }
    },

    _onInputLoveCode(ev) {
        this.validLoveCode = false;
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.el.querySelector("#validate_love_code").disabled = !re.test(ev.target.value);
    },

    async _onClickValidateCarrierNumber() {
        try {
            const { saleOrderId, accessToken } = this.getTokenInfo();
            const result = await rpc("/payment/ecpay/check_mobile_barcode/" + saleOrderId, {
                access_token: accessToken,
                carrier_number: this.el.querySelector("#l10n_tw_edi_carrier_number").value,
            });
            if (result) {
                this.validCarrierNumber = true;
                this.showValidateCarrierNumber = false;
                this.showReenterCarrierNumber = true;
                this.el.querySelector("#l10n_tw_edi_carrier_number").setAttribute("readonly", true);
            } else {
                this.call("dialog", "add", WarningDialog, {
                    title: _t("Error"),
                    message: _t("Storage Code is invalid"),
                });
            }
        } catch (error) {
            this.call("dialog", "add", WarningDialog, {
                title: _t("ECpay Error"),
                message: error.data.message,
            });
        }
        this.showInvoiceItems();
    },

    async _onClickValidateLoveCode() {
        try {
            const { saleOrderId, accessToken } = this.getTokenInfo();
            const result = await rpc("/payment/ecpay/check_love_code/" + saleOrderId, {
                access_token: accessToken,
                love_code: this.el.querySelector("#l10n_tw_edi_love_code").value,
            });

            if (result) {
                this.validLoveCode = true;
                this.showValidateLoveCode = false;
                this.showReenterLoveCode = true;
                this.el.querySelector("#l10n_tw_edi_love_code").setAttribute("readonly", true);
            } else {
                this.call("dialog", "add", WarningDialog, {
                    title: _t("Error"),
                    message: _t("Love code is invalid"),
                });
            }
        } catch (error) {
            this.call("dialog", "add", WarningDialog, {
                title: _t("ECpay Error"),
                message: error.data.message,
            });
        }
        this.showInvoiceItems();
    },

    _onClickReenterCarrierNumber() {
        this.validCarrierNumber = false;
        this.showValidateCarrierNumber = true;
        this.showReenterCarrierNumber = false;
        this.el.querySelector("#l10n_tw_edi_carrier_number").removeAttribute("readonly");
        this.showInvoiceItems();
    },

    _onClickReenterLoveCode() {
        this.validLoveCode = false;
        this.showValidateLoveCode = true;
        this.showReenterLoveCode = false;
        this.el.querySelector("#l10n_tw_edi_love_code").removeAttribute("readonly");
        this.showInvoiceItems();
    },
});
