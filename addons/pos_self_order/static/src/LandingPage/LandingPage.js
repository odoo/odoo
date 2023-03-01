/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    setup() {
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
        this.env.state.currentProduct = 0;
    }
}
