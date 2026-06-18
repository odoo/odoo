import { Component, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class UnavailableProductsDialog extends Component {
    static template = "pos_self_order.UnavailableProductsDialog";
    static components = { Dialog };
    props = props({
        productNames: t.array(),
        onClose: t.function().optional(),
        close: t.function().optional(),
    });

    onConfirm() {
        this.props.onClose();
        this.props.close();
    }
}
