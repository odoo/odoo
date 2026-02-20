import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };
    static props = {
        amount: { type: String },
        confirm: { type: Function, optional: true },
        cancel: { type: Function, optional: true },
        close: { type: Function, optional: true },
        isConfirmBtnShown: { type: Boolean, optional: true },
        paymentMethod: { type: Object, optional: true },
        qrCode: { type: String },
        line: { type: Object, optional: true },
    };
    static defaultProps = {
        confirm: () => {},
        cancel: () => {},
        close: () => {},
        isConfirmBtnShown: true,
        paymentMethod: {},
        line: {},
    };

    confirm() {
        this.props.confirm();
        this.props.close();
    }
}
