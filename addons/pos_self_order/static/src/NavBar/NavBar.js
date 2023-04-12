/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
export class NavBar extends Component {
    static template = "pos_self_order.NavBar";
    static props = { previousPage: String };
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
