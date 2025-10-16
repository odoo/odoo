import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };

    static props = {
        amount: { type: String },
        qrCode: { type: String },
        confirm: { type: Function, optional: true },
        confirmLabel: { type: String, optional: true },
        cancel: { type: Function, optional: true },
        cancelLabel: { type: String, optional: true },
        close: { type: Function, optional: true },
        isCustomerDisplay: { type: Boolean, optional: true },
        footer: { type: Boolean, optional: true },
    };
    static defaultProps = { footer: true, cancelLabel: "Discard", confirmLabel: "Confirm" };

    setup() {
        this.state = useState({ qrLoaded: false });
    }

    onQrLoaded() {
        // Force the skeleton to avoid flashing effect
        setTimeout(() => {
            this.state.qrLoaded = true;
        }, 150);
    }

    confirm() {
        this.props.confirm();
        this.props.close();
    }
}
