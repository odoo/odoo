import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class UnavailableProductsDialog extends Component {
    static template = "pos_self_order.UnavailableProductsDialog";
    static components = { Dialog };
    static props = {
        productNames: { type: Array },
        onClose: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    onConfirm() {
        this.props.onClose();
        this.props.close();
    }
}
