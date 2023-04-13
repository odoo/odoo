/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
export class NavBar extends Component {
    static template = "pos_self_order.NavBar";
    static props = {
        customText: { type: String, optional: true },
        goBack: { type: String },
        class: { type: String, optional: true },
    };
    static defaultProps = { class: "" };
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
