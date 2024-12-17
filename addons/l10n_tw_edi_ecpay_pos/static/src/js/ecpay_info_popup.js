import { Component, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

const CARRIER_TYPE = Object.freeze({
    0: "",
    1: "Merchant Carrier",
    2: "Citizen Digital Certificate",
    3: "Mobile Barcode",
    4: "EasyCard",
    5: "iPass",
});
const CARRIERS_REQUIRE_NUMBER = Object.freeze(["2", "3", "4", "5"]);
const SMART_CARD_CARRIERS = Object.freeze(["4", "5"]);

export class EcpayInfoPopup extends Component {
    static template = "l10n_tw_edi_ecpay_pos.EcpayInfoPopup";
    static components = { Dialog };
    static props = {
        getPayload: Function,
        close: Function,
    };
    carrierType = CARRIER_TYPE;

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        const order = this.pos.get_order();
        this.data = {};
        this.state = useState({
            isDonate: Boolean(order.l10n_tw_edi_love_code),
            loveCode: order.l10n_tw_edi_love_code || "",
            carrierType: order.l10n_tw_edi_carrier_type || "1",
            carrierNumber: order.l10n_tw_edi_carrier_number || "",
            carrierNumber2: order.l10n_tw_edi_carrier_number_2 || "",
            validCarrierNumber: false,
            validLoveCode: false,
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
            this.state.carrierType === "3" &&
            Boolean(re.test(this.state.carrierNumber)) &&
            !this.state.validCarrierNumber
        );
    }

    get showValidateLoveCode() {
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        return (
            this.state.isDonate &&
            Boolean(re.test(this.state.loveCode)) &&
            !this.state.validLoveCode
        );
    }

    get showReEnterCarrierNumber() {
        return (
            !this.state.isDonate && this.state.carrierType === "3" && this.state.validCarrierNumber
        );
    }

    get showReEnterLoveCode() {
        return this.state.isDonate && this.state.validLoveCode;
    }

    get carrierNumberPlaceholder() {
        const carrierType = this.state.carrierType;
        if (carrierType === "2") {
            return _t("2 capital letters following 14 digits");
        }
        if (carrierType === "3") {
            return _t("/ following 7 alphanumeric or +-. string");
        }
        if (SMART_CARD_CARRIERS.includes(carrierType)) {
            return _t("Card hidden code");
        }
        return false;
    }

    get carrierNumberPlaceholder2() {
        return _t("Card visible code");
    }

    _showAlert(title, message) {
        this.dialog.add(AlertDialog, {
            title: title,
            body: _t(message),
        });
    }

    async _onClickValidateCarrierNumber() {
        try {
            const result = await this.pos.data.call(
                "pos.order",
                "l10n_tw_edi_check_mobile_barcode",
                [this.state.carrierNumber]
            );
            if (result) {
                this.state.validCarrierNumber = true;
            }
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        }
    }

    async _onClickValidateLoveCode() {
        try {
            const result = await this.pos.data.call("pos.order", "l10n_tw_edi_check_love_code", [
                this.state.loveCode,
            ]);
            if (result) {
                this.state.validLoveCode = true;
            }
        } catch (error) {
            this._showAlert(_t("ECpay Error"), error.data.message);
        }
    }

    _onClickReenterCarrierNumber() {
        this.state.validCarrierNumber = false;
    }

    _onClickReenterLoveCode() {
        this.state.validLoveCode = false;
    }

    _validateData() {
        if (this.state.isDonate && !this.state.validLoveCode) {
            return [false, _t("Please enter correct love code")];
        }

        if (
            !this.state.isDonate &&
            ((this.state.carrierType === "2" &&
                !/^[A-Z]{2}[0-9]{14}$/.test(this.state.carrierNumber)) ||
                (this.state.carrierType === "3" && !this.state.validCarrierNumber))
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
