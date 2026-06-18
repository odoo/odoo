import { Component, props, t } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

export class CancelPopup extends Component {
    static template = "pos_self_order.CancelPopup";
    props = props({
        title: t.string(),
        confirm: t.function(),
        close: t.function(),
    });

    setup() {
        this.selfOrder = useSelfOrder();
    }

    confirm() {
        this.props.close();
        this.props.confirm();
    }
}
