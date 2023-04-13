/** @odoo-module */

import { useSelfOrder } from "@pos_self_order/SelfOrderService";

const { Component } = owl;

export class FloatingButton extends Component {
    static template = "FloatingButton";
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
export default { FloatingButton };
