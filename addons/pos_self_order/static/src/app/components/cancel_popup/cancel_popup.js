/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";

export class CancelPopup extends Component {
    static template = "pos_self_order.CancelPopup";
    static props = {
        confirm: Function,
        close: Function,
    };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    confirm() {
        this.props.close();
        this.props.confirm();
    }
}
