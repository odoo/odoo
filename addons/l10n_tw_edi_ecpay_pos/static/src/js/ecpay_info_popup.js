import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";

export class EcpayInfoPopup extends Component {
    static template = "l10n_tw_edi_ecpay_pos.EcpayInfoPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        getPayload: Function,
        close: Function,
        newPartner: { optional: true },
    };

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        const order = this.props.order;
        const partner = order.get_partner() || this.props.newPartner;
        this.validCarrierNumber = false;
        this.validLoveCode = false;
        this.state = useState({
            carrierType: order.l10n_tw_edi_carrier_type || "1",
            showCarrierType: !order?.l10n_tw_edi_love_code,
            showCarrierNumber: ["2", "3", "4", "5"].includes(order.l10n_tw_edi_carrier_type),
            showCarrierNumber2: ["4", "5"].includes(order.l10n_tw_edi_carrier_type),
            showValidateCarrierNumber:
                Boolean(order?.l10n_tw_edi_carrier_number) &&
                ["2", "3"].includes(order.l10n_tw_edi_carrier_type),
            showValidateLoveCode: Boolean(order?.l10n_tw_edi_love_code),
            showReEnterCarrierNumber: false,
            showReEnterLoveCode: false,
            carrierNumberPlaceholder: false,
            data: {},
        });

        onMounted(() => {
            if (partner) {
                document.querySelector("#l10n_tw_edi_love_code").value =
                    order.l10n_tw_edi_love_code || "";
                document.querySelector("#l10n_tw_edi_carrier_number").value =
                    order.l10n_tw_edi_carrier_number || "";
                document.querySelector("#l10n_tw_edi_carrier_number_2").value =
                    order.l10n_tw_edi_carrier_number_2 || "";
            }
        });
    }

    _onClickDonate(ev) {
        this.state.showCarrierType = !ev.target.checked;
    }

    _onChangeCarrierType(ev) {
        const carrierType = ev.target.value;
        if (carrierType === "2") {
            this.state.carrierNumberPlaceholder = _t("2 capital letters following 14 digits");
            this.state.showCarrierNumber = true;
            this.state.showCarrierNumber2 = false;
        } else if (carrierType === "3") {
            this.state.carrierNumberPlaceholder = _t("/ following 7 alphanumeric or +-. string");
            this.state.showCarrierNumber = true;
            this.state.showCarrierNumber2 = false;
        } else if (["4", "5"].includes(carrierType)) {
            this.state.carrierNumberPlaceholder = "";
            this.state.showCarrierNumber = true;
            this.state.showCarrierNumber2 = true;
        } else {
            this.state.showCarrierNumber = false;
            this.state.showCarrierNumber2 = false;
        }
        this.validCarrierNumber = false;
        this.state.carrierType = carrierType;
    }

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
    }

    _onInputLoveCode(ev) {
        const re = /^([xX]{1}[0-9]{2,6}|[0-9]{3,7})$/;
        this.state.showValidateLoveCode = Boolean(re.test(ev.target.value));
    }

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
    }

    async _onClickValidateLoveCode() {
        try {
            const result = await this.pos.data.call("pos.order", "l10n_tw_edi_check_love_code", [
                document.querySelector("#l10n_tw_edi_love_code").value,
            ]);
            if (result) {
                this.validLoveCode = true;
                this.state.showValidateLoveCode = false;
                this.state.showReEnterLoveCode = true;
            }
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("ECpay Error"),
                body: error.data.message,
            });
        }
    }

    _onClickReenterCarrierNumber() {
        this.validCarrierNumber = false;
        this.state.showValidateCarrierNumber = true;
        this.state.showReEnterCarrierNumber = false;
    }

    _onClickReenterLoveCode() {
        this.validLoveCode = false;
        this.state.showValidateLoveCode = true;
        this.state.showReEnterLoveCode = false;
    }

    // eslint-disable-next-line complexity
    validateData() {
        const carrierNumber = document.querySelector("#l10n_tw_edi_carrier_number").value;
        const carrierNumber2 = document.querySelector("#l10n_tw_edi_carrier_number_2").value;

        if (!this.state.showCarrierType && !this.validLoveCode) {
            return [false, "Please enter correct love code"];
        }
        if (
            this.state.showCarrierType &&
            this.state.showCarrierNumber &&
            !this.state.showCarrierNumber2 &&
            !this.validCarrierNumber
        ) {
            return [false, "Please enter correct carrier number"];
        }

        if (
            this.state.showCarrierType &&
            this.state.showCarrierNumber &&
            this.state.showCarrierNumber2 &&
            (!carrierNumber || !carrierNumber2)
        ) {
            return [false, "Please enter carrier number and carrier number 2"];
        }

        if (!this.state.showCarrierType) {
            this.state.data.loveCode = document.querySelector("#l10n_tw_edi_love_code").value;
        }
        if (this.state.showCarrierType) {
            this.state.data.carrierType = document.querySelector("#l10n_tw_edi_carrier_type").value;
            if (this.state.showCarrierNumber) {
                this.state.data.carrierNumber = carrierNumber;
            }
            if (this.state.showCarrierNumber2) {
                this.state.data.carrierNumber2 = carrierNumber2;
            }
        }
        return [true, "Data is valid"];
    }

    confirm() {
        const [is_valid, valid_message] = this.validateData();
        if (is_valid) {
            this.props.getPayload(this.state);
            this.props.close();
        } else {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t(valid_message),
            });
            return;
        }
    }
}
