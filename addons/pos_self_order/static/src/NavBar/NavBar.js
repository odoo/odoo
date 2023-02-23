/** @odoo-module */

import { useSelfOrder } from "@pos_self_order/SelfOrderService";

const { Component } = owl;

export class NavBar extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
NavBar.template = "NavBar";
export default { NavBar };
