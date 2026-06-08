import { Component, props, types } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class UnavailableProductsDialog extends Component {
    static template = "pos_self_order.UnavailableProductsDialog";
    static components = { Dialog };
    props = props({
        productNames: types.array(),
        "onClose?": types.function(),
        "close?": types.function(),
    });

    onConfirm() {
        this.props.onClose();
        this.props.close();
    }
}
