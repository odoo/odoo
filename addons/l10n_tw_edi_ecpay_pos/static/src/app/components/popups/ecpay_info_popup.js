import { Component, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

const CARRIER_TYPES = Object.freeze({
    MEMBER_ACCOUNT: "1",
    CITIZEN_DIGITAL_CERTIFICATE: "2",
    MOBILE_BARCODE: "3",
    EASYCARD: "4",
    IPASS: "5",
});
const CARRIERS_REQUIRE_NUMBER = Object.freeze(["2", "3", "4", "5"]);
const SMART_CARD_CARRIERS = Object.freeze(["4", "5"]);
const CARRIER_TYPE_REGEX = /^[A-Z]{2}[0-9]{14}$/;
const MOBILE_BARCODE_REGEX = /^\/[0-9a-zA-Z+-.]{7}$/;
const LOVE_CODE_REGEX = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;

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
        const order = this.pos.getOrder();
        this.data = {};
        this.state = useState({
            isDonate: Boolean(order.l10n_tw_edi_love_code),
            loveCode: order.l10n_tw_edi_love_code || "",
            carrierType: order.l10n_tw_edi_carrier_type || CARRIER_TYPES.MEMBER_ACCOUNT,
            carrierNumber: order.l10n_tw_edi_carrier_number || "",
            carrierNumber2: order.l10n_tw_edi_carrier_number_2 || "",
            validCarrierNumber: false,
            validLoveCode: false,
            isLoading: false,
        });
    }

    get carrierTypes() {
        return Object.freeze({
            [CARRIER_TYPES.MEMBER_ACCOUNT]: _t("Member Account"),
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
        return (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
            MOBILE_BARCODE_REGEX.test(this.state.carrierNumber.trim()) &&
            !this.state.validCarrierNumber
        );
    }

    get showValidateLoveCode() {
        return (
            this.state.isDonate &&
            LOVE_CODE_REGEX.test(this.state.loveCode.trim()) &&
            !this.state.validLoveCode
        );
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
            this.state.isLoading = true;
            this.state.validCarrierNumber = false;
            await this.pos.data.call("pos.session", "l10n_tw_edi_check_mobile_barcode", [
                [this.pos.session.id],
                this.state.carrierNumber.trim(),
            ]);
            this.state.validCarrierNumber = true;
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        } finally {
            this.state.isLoading = false;
        }
    }

    async _onClickValidateLoveCode() {
        try {
            this.state.isLoading = true;
            this.state.validLoveCode = false;
            await this.pos.data.call("pos.session", "l10n_tw_edi_check_love_code", [
                [this.pos.session.id],
                this.state.loveCode.trim(),
            ]);
            this.state.validLoveCode = true;
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        } finally {
            this.state.isLoading = false;
        }
    }

    _validateData() {
        const carrierNumber = this.state.carrierNumber.trim();
        const carrierNumber2 = this.state.carrierNumber2.trim();
        const loveCode = this.state.loveCode.trim();
        if (this.state.isDonate) {
            if (!loveCode) {
                return [false, _t("Please enter a love code")];
            }
            if (!LOVE_CODE_REGEX.test(loveCode)) {
                return [false, _t("Please enter a valid love code (3-7 digits)")];
            }
            if (!this.state.validLoveCode) {
                return [false, _t("Please validate the love code before continuing")];
            }
        }
        if (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.CITIZEN_DIGITAL_CERTIFICATE &&
            !CARRIER_TYPE_REGEX.test(carrierNumber)
        ) {
            return [
                false,
                _t("Please enter a valid carrier number (2 capital letters followed by 14 digits)"),
            ];
        }

        if (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
            !MOBILE_BARCODE_REGEX.test(carrierNumber)
        ) {
            return [
                false,
                _t(
                    "Please enter a valid mobile barcode (/ following 7 alphanumeric or +-. string)"
                ),
            ];
        }

        if (
            !this.state.isDonate &&
            this.state.carrierType === CARRIER_TYPES.MOBILE_BARCODE &&
            !this.state.validCarrierNumber
        ) {
            return [false, _t("Please validate the carrier number before continuing")];
        }

        if (
            !this.state.isDonate &&
            SMART_CARD_CARRIERS.includes(this.state.carrierType) &&
            (!carrierNumber || !carrierNumber2)
        ) {
            return [false, _t("Please enter carrier number and carrier number 2")];
        }

        if (this.state.isDonate) {
            this.data.loveCode = loveCode;
        } else {
            this.data.carrierType = this.state.carrierType;
            if (this.showCarrierNumber) {
                this.data.carrierNumber = carrierNumber;
            }
            if (this.showCarrierNumber2) {
                this.data.carrierNumber2 = carrierNumber2;
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
