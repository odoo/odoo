/** @odoo-module **/
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { WebsiteSale } from "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        "change #l10n_tw_edi_is_donate": "_onChangeDonateCheckbox",
        "change #l10n_tw_edi_carrier_type": "_onChangeCarrierType",
        "input #l10n_tw_edi_carrier_number": "_onInputCarrierNumber",
        "input #l10n_tw_edi_love_code": "_onInputLoveCode",
        "click #validate_carrier_number": "_onClickValidateCarrierNumber",
        "click #validate_love_code": "_onClickValidateLoveCode",
        "click #reenter_carrier_number": "_onClickReenterCarrierNumber",
        "click #reenter_love_code": "_onClickReenterLoveCode",
    }),

    init() {
        this._super(...arguments);
        this._onClickValidateCarrierNumber = debounce(
            this._onClickValidateCarrierNumber.bind(this),
            500
        );
        this._onClickValidateLoveCode = debounce(this._onClickValidateLoveCode.bind(this), 500);
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
                document.querySelector("#l10n_tw_edi_carrier_type").value === "3" &&
                document.querySelector("#l10n_tw_edi_carrier_number").value !== ""
            ) {
                this.showValidateCarrierNumber = true;
                document.querySelector("#validate_carrier_number").classList.remove("d-none");
            }
            this.showValidateLoveCode = false;
            if (document.querySelector("#l10n_tw_edi_love_code").value !== "") {
                this.showValidateLoveCode = true;
                document.querySelector("#validate_love_code").classList.remove("d-none");
            }
        }
    },

    getTokenInfo() {
        const form = document.getElementById("ecpay_invoice_form");
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
        ]);

        elementsToShow.forEach((isShown, selector) => {
            this.el.querySelector(selector).classList.toggle("d-none", !isShown);
        });
    },

    _onChangeDonateCheckbox(ev) {
        const isChecked = ev.target.checked;
        this.showLoveCode = isChecked;
        this.showCarrierType = !isChecked;
        this.showInvoiceItems();
    },

    _onChangeCarrierType(ev) {
        const carrierType = ev.target.value;
        if (carrierType === "2") {
            document.querySelector("#l10n_tw_edi_carrier_number").placeholder = _t(
                "2 capital letters following 14 digits"
            );
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber = false;
        } else if (carrierType === "3") {
            document.querySelector("#l10n_tw_edi_carrier_number").placeholder = _t(
                "/ following 7 alphanumeric or +-. string"
            );
            this.showCarrier = true;
            this.showCarrier2 = false;
            this.showValidateCarrierNumber =
                document.querySelector("#l10n_tw_edi_carrier_number").value !== "";
        } else if (["4", "5"].includes(carrierType)) {
            document.querySelector("#l10n_tw_edi_carrier_number").placeholder = "";
            this.showCarrier = true;
            this.showCarrier2 = true;
            this.showValidateCarrierNumber = false;
            document.querySelector("#l10n_tw_edi_carrier_number").placeholder =
                _t("Card hidden code");
            document.querySelector("#l10n_tw_edi_carrier_number_2").placeholder =
                _t("Card visible code");
        } else {
            this.showCarrier = false;
            this.showCarrier2 = false;
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
            this.showValidateCarrierNumber = re.test(ev.target.value);
        } else {
            this.showValidateCarrierNumber = false;
        }
        this.showInvoiceItems();
    },

    _onInputLoveCode(ev) {
        this.validLoveCode = false;
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.showValidateLoveCode = re.test(ev.target.value);
        this.showInvoiceItems();
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
                this.el.querySelector("#reenter_carrier_number").classList.remove("d-none");
                this.el.querySelector("#l10n_tw_edi_carrier_number").readonly = true;
            } else {
                this.call("dialog", "add", WarningDialog, {
                    title: _t("Error"),
                    message: _t("Carrier number is invalid"),
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
                this.el.querySelector("#reenter_love_code").classList.remove("d-none");
                this.el.querySelector("#l10n_tw_edi_love_code").readOnly = true;
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
        this.el.querySelector("#reenter_carrier_number").classList.add("d-none");
        this.el.querySelector("#l10n_tw_edi_carrier_number").removeAttribute("readonly");
        this.showInvoiceItems();
    },

    _onClickReenterLoveCode() {
        this.validLoveCode = false;
        this.showValidateLoveCode = true;
        this.el.querySelector("#reenter_love_code").classList.add("d-none");
        this.el.querySelector("#l10n_tw_edi_love_code").removeAttribute("readonly");
        this.showInvoiceItems();
    },
});
