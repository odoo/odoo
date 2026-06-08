import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, proxy, t } from "@odoo/owl";

export const qrPopupProps = {
    amount: t.string(),
    qrCode: t.string(),
    confirm: t.function().optional(),
    confirmLabel: t.string().optional("Confirm"),
    cancel: t.function().optional(),
    cancelLabel: t.string().optional("Discard"),
    close: t.function().optional(),
    footer: t.boolean().optional(true),
    provider: t.or([t.string(), t.boolean()]).optional(),
};

export class QRPopup extends Component {
    static template = "point_of_sale.QRPopup";
    static components = { Dialog };

    props = props(qrPopupProps);

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
