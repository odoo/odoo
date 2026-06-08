import { Component, props, types } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

export class CancelPopup extends Component {
    static template = "pos_self_order.CancelPopup";
    props = props({
        title: types.string(),
        confirm: types.function(),
        close: types.function(),
    });

    setup() {
        this.selfOrder = useSelfOrder();
    }

    confirm() {
        this.props.close();
        this.props.confirm();
    }
}
