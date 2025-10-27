import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };
    static props = {
        amount: { type: String },
        confirm: { type: Function, optional: true, default: false },
        cancel: { type: Function, optional: true, default: false },
        close: { type: Function, optional: true, default: false },
        isCustomerDisplay: { type: Boolean, optional: true, default: false },
        paymentMethod: { type: Object, optional: true, default: {} },
        qrCode: { type: String },
        line: { type: Object, optional: true, default: null },
    };

    confirm() {
        this.props.confirm();
        this.props.close();
    }
}
