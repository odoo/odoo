import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.currentOrder.set_to_invoice(true);
        this.validIdentifier = false;
        this.validCarrierNumber = false;
        this.validLoveCode = false;
        this.state = useState({
            showAddress: false,
            showLoveCode: false,
            showCarrierType: true,
            showCarrierNumber: false,
            showIdentifierGroup: false,
            showIdentifierData: false,
            showValidateCarrierNumber: false,
            showValidateLoveCode: false,
            showReEnterCarrierNumber: false,
            showReEnterateLoveCode: false,
            carrierNumberPlaceholder: false,
            isRefund: this.currentOrder.get_orderlines().some((line) => line.refunded_orderline_id),
        });
    },

    onMounted() {
        super.onMounted(...arguments);
        document.querySelector("#identifier").value = this.currentOrder.get_partner().vat || "";
        document.querySelector("#l10n_tw_edi_customer_name").value =
            this.currentOrder.get_partner().name || "";
        document.querySelector("#l10n_tw_edi_customer_email").value =
            this.currentOrder.get_partner().email || "";
        document.querySelector("#l10n_tw_edi_customer_phone").value =
            this.currentOrder.get_partner().phone || "";
        document.querySelector("#l10n_tw_edi_customer_address").value =
            this.currentOrder.get_partner().contact_address || "";
    },

    _onChangePrintGroup(ev) {
        const printGroup = ev.target.value;
        if (printGroup === "0") {
            this.state.showAddress = false;
            this.state.showLoveCode = false;
            this.state.showCarrierType = true;
            this.state.showIdentifierGroup = false;
        } else if (printGroup === "1") {
            this.state.showAddress = true;
            this.state.showLoveCode = false;
            this.state.showCarrierType = false;
            this.state.showIdentifierGroup = true;
        } else {
            this.state.showAddress = false;
            this.state.showLoveCode = true;
            this.state.showCarrierType = false;
            this.state.showIdentifierGroup = false;
        }
    },

    _onChangeCarrierType(ev) {
        const carrierType = ev.target.value;
        if (carrierType === "2") {
            this.state.carrierNumberPlaceholder = _t("2 capital letters following 14 digits");
            this.state.showCarrierNumber = true;
        } else if (carrierType === "3") {
            this.state.carrierNumberPlaceholder = _t("/ following 7 alphanumeric or +-. string");
            this.state.showCarrierNumber = true;
        } else {
            this.state.showCarrierNumber = false;
        }
        this.validCarrierNumber = false;
    },

    _onChangeIdentifierGroup(ev) {
        this.state.showIdentifierData = Boolean(parseInt(ev.target.value, 10));
    },

    _onInputCarrierNumber(ev) {
        const carrierType = document.querySelector("#l10n_tw_edi_carrier_type").value;
        if (carrierType === "2") {
            const re = /^[A-Z]{2}[0-9]{14}$/;
            this.validCarrierNumber = Boolean(re.test(ev.target.value));
        } else if (carrierType === "3") {
            const re = /^\/[0-9a-zA-Z+-.]{7}$/;
            this.state.showValidateCarrierNumber = Boolean(re.test(ev.target.value));
        } else {
            this.state.showValidateCarrierNumber = false;
        }
    },

    _onInputLoveCode(ev) {
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.state.showValidateLoveCode = Boolean(re.test(ev.target.value));
    },

    async _onClickValidateCarrierNumber() {
        try {
            const result = await this.pos.data.call(
                "pos.order",
                "l10n_tw_edi_check_mobile_barcode",
                [document.querySelector("#l10n_tw_edi_carrier_number").value]
            );
            if (result) {
                this.validCarrierNumber = true;
                this.state.showValidateCarrierNumber = false;
                this.state.showReEnterCarrierNumber = true;
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.data.message,
            });
        }
    },

    async _onClickValidateLoveCode() {
        try {
            const result = await this.pos.data.call("pos.order", "l10n_tw_edi_check_love_code", [
                document.querySelector("#l10n_tw_edi_love_code").value,
            ]);
            if (result) {
                this.validLoveCode = true;
                this.state.showValidateLoveCode = false;
                this.state.showReEnterateLoveCode = true;
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.data.message,
            });
        }
    },

    async _onClickValidateTaxID() {
        try {
            const result = await this.pos.data.call("pos.order", "l10n_tw_edi_check_tax_id", [
                document.querySelector("#identifier").value,
            ]);
            if (result) {
                this.dialog.add(AlertDialog, {
                    title: _t("Success"),
                    body: _t("Tax ID is valid"),
                });
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.data.message,
            });
        }
    },

    _onClickReenterCarrierNumber() {
        this.validCarrierNumber = false;
        this.state.showValidateCarrierNumber = true;
        this.state.showReEnterCarrierNumber = false;
    },

    _onClickReenterLoveCode() {
        this.validLoveCode = false;
        this.state.showValidateLoveCode = true;
        this.state.showReEnterateLoveCode = false;
    },

    validateData() {
        const customerEmail = document.querySelector("#l10n_tw_edi_customer_email").value;
        const customerPhone = document.querySelector("#l10n_tw_edi_customer_phone").value;
        const identifier = document.querySelector("#identifier").value;
        if (
            this.state.showAddress &&
            this.state.showIdentifierData &&
            !(identifier && (customerEmail || customerPhone))
        ) {
            return false;
        }
        if (this.state.showLoveCode && !this.validLoveCode) {
            return false;
        }
        if (
            this.state.showCarrierType &&
            this.state.showCarrierNumber &&
            !this.validCarrierNumber
        ) {
            return false;
        }
        const data = {
            invoiceType: document.querySelector("#l10n_tw_edi_invoice_type").value,
        };

        if (this.state.showAddress) {
            data.printFlag = true;
        }
        if (this.state.showLoveCode) {
            data.loveCode = document.querySelector("#l10n_tw_edi_love_code").value;
        }
        if (this.state.showCarrierType) {
            data.carrierType = document.querySelector("#l10n_tw_edi_carrier_type").value;
            if (this.state.showCarrierNumber) {
                data.carrierNumber = document.querySelector("#l10n_tw_edi_carrier_number").value;
            }
        }
        return data;
    },

    async _finalizeValidation() {
        const data = this.validateData();
        if (data) {
            this.currentOrder.set_invoice_info(
                "printFlag" in data ? data.printFlag : false,
                "loveCode" in data ? data.loveCode : false,
                "carrierType" in data ? data.carrierType : false,
                "carrierNumber" in data ? data.carrierNumber : false,
                data.invoiceType,
            );
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("Please enter correct information"),
            });
            return;
        }
        await super._finalizeValidation(...arguments);
    },
});
