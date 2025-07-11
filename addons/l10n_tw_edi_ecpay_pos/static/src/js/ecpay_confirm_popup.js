import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class EcpayConfirmPopup extends Component {
    static template = "l10n_tw_edi_ecpay_pos.EcpayConfirmPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        getPayload: Function,
        close: Function,
        newPartner: { optional: true },
    };

    confirm_yes() {
        this.props.getPayload({
            confirm: 1,
        });
        this.props.close();
    }
    confirm_no() {
        this.props.getPayload({
            confirm: 0,
        });
        this.props.close();
    }
}
