import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.showAddress = false;
        this.showLoveCode = false;
        this.showCarrierType = true;
        this.showCarrier = false;
        this.showIdentifier = false;
        this.showIdentifierData = false;
        this.validIdentifier = false;
        this.validcarrier_number = false;
        this.validLoveCode = false;
        this.currentOrder.set_to_invoice(true);
        this.state = useState({
            isRefund: this.currentOrder.get_orderlines().some(line => line.refunded_orderline_id),
        });
    },

    onMounted() {
        super.onMounted(...arguments);
        document.querySelector("#l10n_tw_edi_customer_name").value = this.currentOrder.get_partner().name || ''
        document.querySelector("#l10n_tw_edi_customer_email").value = this.currentOrder.get_partner().email || ''
        document.querySelector("#l10n_tw_edi_customer_phone").value = this.currentOrder.get_partner().phone || ''
        document.querySelector("#l10n_tw_edi_customer_address").value = this.currentOrder.get_partner().contact_address || ''
    },

    showInvoiceItems() {
        const elementsToShow = new Map([
            ["#div-l10n_tw_edi_customer_address", this.showAddress],
            ["#ecpay_invoice_love_code", this.showLoveCode],
            ["#ecpay_carrier_type_group", this.showCarrierType],
            ["#ecpay_invoice_carrier_number", this.showCarrier],
            ["#ecpay_invoice_identifier_group", this.showIdentifier],
            ["#ecpay_invoice_customer_name", this.showIdentifierData]
          ]);

        elementsToShow.forEach((isShown, selector) => {
          document.querySelector(selector).style.display =  isShown ?  'block' : 'none'
        })
    },

    triggerWarning(warningId, errorId, valid) {
        document.querySelector(warningId).style.display =  valid ?  'none' : 'block'
        document.querySelector(errorId).classList.toggle("has-error", !valid)
    },

    _onChangePrintGroup(ev) {
        const printGroup = ev.target.value;
        if (printGroup === "0") {
            this.showAddress = false;
            this.showLoveCode = false;
            this.showCarrierType = true;
            this.showIdentifier = false;
        } else if (printGroup === "1") {
            this.showAddress = true;
            this.showLoveCode = false;
            this.showCarrierType = false;
            this.showIdentifier = true;
        } else {
            this.showAddress = false;
            this.showLoveCode = true;
            this.showCarrierType = false;
            this.showIdentifier = false;
        }
        this.showInvoiceItems();
    },

    _onChangeCarrierType(ev) {
        const CarrierType = ev.target.value;
        if (CarrierType === "2") {
            document.querySelector("#warning-l10n_tw_edi_carrier_number").innerHTML =
                "Correct Format: 2 capital letters following 14 digits";
            this.showCarrier = true;
        } else if (CarrierType === "3") {
            document.querySelector("#warning-l10n_tw_edi_carrier_number").innerHTML =
                'Correct Format: "/" following 7 alphanumeric or +-. string';
            this.showCarrier = true;
        } else {
            this.showCarrier = false;
        }
        this.validcarrier_number = false;
        document.querySelector("#warning-l10n_tw_edi_carrier_number").style.display = "block";
        this.showInvoiceItems();
    },

    _onChangeIdentifierGroup(ev) {
        this.showIdentifierData = Boolean(parseInt(ev.target.value, 10));
        this.showInvoiceItems();
    },

    _onInputIdentifier(ev) {
        const re = /^[0-9]{8}$/;
        this.validIdentifier = Boolean(re.test(ev.target.value));
        this.triggerWarning("#warning-identifier", "#div-identifier", this.validIdentifier);
        if (this.validIdentifier) {
            document.querySelector("#validate_tax_id").style.display = "block";
        }
        else {
            document.querySelector("#validate_tax_id").style.display = "none";
        }
    },

    _onInputCarrierNumber(ev) {
        const CarrierType = document.querySelector("#l10n_tw_edi_carrier_type").value;
        if (CarrierType === "2") {
            document.querySelector("#warning-l10n_tw_edi_carrier_number").innerHTML =
                "Correct Format: 2 capital letters following 14 digits";
            const re = /^[A-Za-z]{2}[0-9]{14}$/;
            this.validcarrier_number = Boolean(re.test(ev.target.value));
            this.triggerWarning(
                "#warning-l10n_tw_edi_carrier_number",
                "#ecpay_invoice_carrier_number",
                this.validcarrier_number
            );
        } else if (CarrierType === "3") {
            document.querySelector("#warning-l10n_tw_edi_carrier_number").innerHTML =
                "Correct Format: '/' following 7 alphanumeric or +-. string";
            const re = /^\/{1}[0-9a-zA-Z+-.]{7}$/;
            if (re.test(ev.target.value)) {
                document.querySelector("#validate_carrier_number").style.display = "block";
                this.triggerWarning("#warning-l10n_tw_edi_carrier_number", "#ecpay_invoice_carrier_number", true);
            } else {
                document.querySelector("#validate_carrier_number").style.display = "none";
                this.triggerWarning(
                    "#warning-l10n_tw_edi_carrier_number",
                    "#ecpay_invoice_carrier_number",
                    this.validcarrier_number
                );
            }
        } else {
            document.querySelector("#validate_carrier_number").style.display = "none";
            this.triggerWarning(
                "#warning-l10n_tw_edi_carrier_number",
                "#ecpay_invoice_carrier_number",
                this.validcarrier_number
            );
        }
    },

    _onInputLoveCode(ev) {
        document.querySelector("#warning-l10n_tw_edi_love_code").innerHTML = "Love code format is 3-7 digits";
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        if (re.test(ev.target.value)) {
            document.querySelector("#validate_love_code").style.display = "block";
            this.triggerWarning("#warning-l10n_tw_edi_love_code", "#ecpay_invoice_love_code", true);
        } else {
            document.querySelector("#validate_love_code").style.display = "none";
            this.triggerWarning("#warning-l10n_tw_edi_love_code", "#ecpay_invoice_love_code", this.validcarrier_number);
        }
    },

    async _onClickValidateCarrierNumber() {
        try{
            const result = await this.pos.data.call(
                "account.move",
                "l10n_tw_edi_check_mobile_barcode",
                [document.querySelector("#l10n_tw_edi_carrier_number").value],
            );
            if (result) {
                this.validcarrier_number = true;
                this.triggerWarning(
                    "#warning-l10n_tw_edi_carrier_number",
                    "#ecpay_invoice_carrier_number",
                    this.validcarrier_number
                );
                document.querySelector("#validate_carrier_number").style.display = "none";
                document.querySelector("#reenter_carrier_number").style.display = "block";
                document.querySelector("#l10n_tw_edi_carrier_number").disabled = true;
            } else {
                document.querySelector("#warning-l10n_tw_edi_carrier_number").innerHTML = "Carrier number does not exist OR Validation failed (Please fill in the ECpay API information in the company setting!)";
                this.triggerWarning(
                    "#warning-l10n_tw_edi_carrier_number",
                    "#ecpay_invoice_carrier_number",
                    this.validcarrier_number
                );
            }
        }
        catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.message.data.message,
            });
        }
    },

    async _onClickValidateLoveCode() {
        try {
            const result = await this.pos.data.call(
                "account.move",
                "l10n_tw_edi_check_love_code",
                [document.querySelector("#l10n_tw_edi_love_code").value],
            );
            if (result) {
                this.validLoveCode = true;
                this.triggerWarning("#warning-l10n_tw_edi_love_code", "#ecpay_invoice_love_code", this.validLoveCode);
                document.querySelector("#validate_love_code").style.display = "none";
                document.querySelector("#reenter_love_code").style.display = "block";
                document.querySelector("#l10n_tw_edi_love_code").disabled = true;
            } else {
                document.querySelector("#warning-l10n_tw_edi_love_code").innerHTML = "Love code does not exist OR Validation failed (Please fill in the ECpay API information in the company setting!)";
                this.triggerWarning("#warning-l10n_tw_edi_love_code", "#ecpay_invoice_love_code", this.validLoveCode);
            }
        }
        catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.message.data.message,
            });
        }
    },

    async _onClickValidateTaxID() {
        try {
            const result = await this.pos.data.call(
                "account.move",
                "l10n_tw_edi_check_tax_id",
                [document.querySelector("#identifier").value],
            );
            if (result) {
                document.querySelector("#l10n_tw_edi_customer_name").value = result;
                document.querySelector("#l10n_tw_edi_customer_address").value = "";
            } else {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("Tax ID is invalid"),
                });
                return false;
            }
        }
        catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.message.data.message,
            });
        }
    },

    _onClickReenterCarrierNumber() {
        this.validcarrier_number = false;
        this.triggerWarning("#warning-l10n_tw_edi_carrier_number", "#ecpay_invoice_carrier_number", this.validcarrier_number);
        document.querySelector("#validate_carrier_number").style.display = "block";
        document.querySelector("#reenter_carrier_number").style.display = "none";
        document.querySelector("#l10n_tw_edi_carrier_number").disabled = false;
    },

    _onClickReenterLoveCode() {
        this.validLoveCode = false;
        this.triggerWarning("#warning-l10n_tw_edi_love_code", "#ecpay_invoice_love_code", this.validLoveCode);
        document.querySelector("#validate_love_code").style.display = "block";
        document.querySelector("#reenter_love_code").style.display = "none";
        document.querySelector("#l10n_tw_edi_love_code").disabled = false;
    },

    validateData() {
        const customerEmail = document.querySelector("#l10n_tw_edi_customer_email").value;
        const customerPhone = document.querySelector("#l10n_tw_edi_customer_phone").value;
        if (this.showAddress && this.showIdentifierData && !(this.validIdentifier && (customerEmail || customerPhone))) {
            return false;
        }
        if (this.showLoveCode && !this.validLoveCode) {
            return false;
        }
        if (this.showCarrierType && this.showCarrier && !this.validCarrierNumber) {
            return false;
        }
        const data = {
            customerEmail,
            customerPhone
        }

        if (this.showAddress) {
            data.printFlag = true;
            data.customerAddress = document.querySelector("#l10n_tw_edi_customer_address").value;
            if (this.showIdentifierData) {
                data.identifier = document.querySelector("#identifier").value;
                data.customerName = document.querySelector("#l10n_tw_edi_customer_name").value;
            }
        }
        if (this.showLoveCode) {
            data.donateFlag = true;
            data.loveCode = document.querySelector("#l10n_tw_edi_love_code").value;
        }
        if (this.showCarrierType) {
            data.CarrierType = document.querySelector("#l10n_tw_edi_carrier_type").value;
            if (this.showCarrier) {
                data.carrierNumber = document.querySelector("#l10n_tw_edi_carrier_number").value;
            }
        }
        return data;
    },

    async _finalizeValidation() {
        const data = this.validateData();
        if (data) {
            this.currentOrder.set_invoice_info(
                'printFlag' in data ? data.printFlag : false,
                'donateFlag' in data ? data.donateFlag : false,
                'loveCode' in data ? data.loveCode : false,
                'identifier' in data ? data.identifier : false,
                'customerName' in data ? data.customerName : "Walk in Customer",
                'customerEmail' in data ? data.customerEmail : false,
                'customerPhone' in data ? data.customerPhone : false,
                'l10n_tw_edi_carrier_type' in data ? data.l10n_tw_edi_carrier_type : false,
                'l10n_tw_edi_carrier_number' in data ? data.l10n_tw_edi_carrier_number : false,
                'customerAddress' in data && data.customerAddress !== '' ? data.customerAddress: " ",
            );
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("Please enter correct information"),
            });
            return;
        }
            await super._finalizeValidation(...arguments);
    }
})
