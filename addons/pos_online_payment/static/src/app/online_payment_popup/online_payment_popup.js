import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
export class OnlinePaymentPopup extends Component {
    static template = "pos_online_payment.OnlinePaymentPopup";
    static components = { Dialog };
    static props = {
        qrCode: String,
        formattedAmount: String,
        orderName: String,
        close: Function,
    };
}
