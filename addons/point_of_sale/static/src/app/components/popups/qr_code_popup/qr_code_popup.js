import { Dialog } from "@web/core/dialog/dialog";
import { Component, proxy, props, types } from "@odoo/owl";

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };
    props = props(
        {
            amount: types.string(),
            qrCode: types.string(),
            "confirm?": types.function(),
            "confirmLabel?": types.string(),
            "cancel?": types.function(),
            "cancelLabel?": types.string(),
            "close?": types.function(),
            "footer?": types.boolean(),
            "provider?": types.or([types.string(), types.boolean()]),
        },
        { footer: true, cancelLabel: "Discard", confirmLabel: "Confirm" }
    );
    setup() {
        this.state = proxy({ qrLoaded: false });
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
