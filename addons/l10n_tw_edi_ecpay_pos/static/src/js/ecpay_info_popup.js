import { Component, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

const CARRIER_TYPES = Object.freeze({
    NONE: "0",
    MERCHANT_CARRIER: "1",
    CITIZEN_DIGITAL_CERTIFICATE: "2",
    MOBILE_BARCODE: "3",
    EASYCARD: "4",
    IPASS: "5",
});
const CARRIERS_REQUIRE_NUMBER = Object.freeze(["2", "3", "4", "5"]);
const SMART_CARD_CARRIERS = Object.freeze(["4", "5"]);
const CARRIER_TYPE_REGEX = /^[A-Z]{2}[0-9]{14}$/;

export class EcpayInfoPopup extends Component {
    static template = "l10n_tw_edi_ecpay_pos.EcpayInfoPopup";
    static components = { Dialog };
    static props = {
        getPayload: Function,
        close: Function,
    };
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        const order = this.pos.get_order();
        this.data = {};
        this.state = useState({
            isDonate: Boolean(order.l10n_tw_edi_love_code),
            loveCode: order.l10n_tw_edi_love_code || "",
            carrierType: order.l10n_tw_edi_carrier_type || CARRIER_TYPES.MERCHANT_CARRIER,
            carrierNumber: order.l10n_tw_edi_carrier_number || "",
            carrierNumber2: order.l10n_tw_edi_carrier_number_2 || "",
            validCarrierNumber: false,
            validLoveCode: false,
        });
    }
    get carrierTypes() {
        return Object.freeze({
            [CARRIER_TYPES.NONE]: _t("None"),
            [CARRIER_TYPES.MERCHANT_CARRIER]: _t("Merchant Carrier"),
            [CARRIER_TYPES.CITIZEN_DIGITAL_CERTIFICATE]: _t("Citizen Digital Certificate"),
            [CARRIER_TYPES.MOBILE_BARCODE]: _t("Mobile Barcode"),
            [CARRIER_TYPES.EASYCARD]: _t("EasyCard"),
            [CARRIER_TYPES.IPASS]: _t("iPass"),
        });
    }

    get showCarrierType() {
        return !this.state.isDonate;
    }

    get showCarrierNumber() {
        return CARRIERS_REQUIRE_NUMBER.includes(this.state.carrierType);
    }

    get showCarrierNumber2() {
        return SMART_CARD_CARRIERS.includes(this.state.carrierType);
    }

    get showValidateCarrierNumber() {
        const re = /^\/[0-9a-zA-Z+-.]{7}$/;
        return (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
            re.test(this.state.carrierNumber) &&
            !this.state.validCarrierNumber
        );
    }

    get showValidateLoveCode() {
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        return this.state.isDonate && re.test(this.state.loveCode) && !this.state.validLoveCode;
    }

    get showReEnterCarrierNumber() {
        return (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
            this.state.validCarrierNumber
        );
    }

    get showReEnterLoveCode() {
        return this.state.isDonate && this.state.validLoveCode;
    }

    get carrierNumberPlaceholder() {
        const carrierType = this.state.carrierType;
        if (carrierType === CARRIER_TYPES.CITIZEN_DIGITAL_CERTIFICATE) {
            return _t("2 capital letters following 14 digits");
        }
        if (carrierType === CARRIER_TYPES.MOBILE_BARCODE) {
            return _t("/ following 7 alphanumeric or +-. string");
        }
        if (SMART_CARD_CARRIERS.includes(carrierType)) {
            return _t("Card hidden code");
        }
        return false;
    }

    _showAlert(title, message) {
        this.dialog.add(AlertDialog, {
            title: title,
            body: message,
        });
    }

    async _onClickValidateCarrierNumber() {
        try {
            await this.pos.data.call("pos.order", "l10n_tw_edi_check_mobile_barcode", [
                this.state.carrierNumber,
            ]);
            this.state.validCarrierNumber = true;
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        }
    }

    async _onClickValidateLoveCode() {
        try {
            await this.pos.data.call("pos.order", "l10n_tw_edi_check_love_code", [
                this.state.loveCode,
            ]);
            this.state.validLoveCode = true;
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        }
    }

    _validateData() {
        if (this.state.isDonate && !this.state.validLoveCode) {
            return [false, _t("Please enter correct love code")];
        }

        if (
            !this.state.isDonate &&
            ((this.state.carrierType === CARRIER_TYPES.CITIZEN_DIGITAL_CERTIFICATE &&
                !CARRIER_TYPE_REGEX.test(this.state.carrierNumber)) ||
                (this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
                    !this.state.validCarrierNumber))
        ) {
            return [false, _t("Please enter valid carrier number")];
        }

        if (
            !this.state.isDonate &&
            SMART_CARD_CARRIERS.includes(this.state.carrierType) &&
            (!this.state.carrierNumber || !this.state.carrierNumber2)
        ) {
            return [false, _t("Please enter carrier number and carrier number 2")];
        }

        if (this.state.isDonate) {
            this.data.loveCode = this.state.loveCode;
        } else {
            this.data.carrierType = this.state.carrierType;
            if (this.showCarrierNumber) {
                this.data.carrierNumber = this.state.carrierNumber;
            }
            if (this.showCarrierNumber2) {
                this.data.carrierNumber2 = this.state.carrierNumber2;
            }
        }
        return [true, _t("Data is valid")];
    }

    confirm() {
        const [is_valid, valid_message] = this._validateData();
        if (is_valid) {
            this.props.getPayload(this.data);
            this.props.close();
        } else {
            this._showAlert(_t("Error"), valid_message);
        }
    }
}
