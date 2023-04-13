/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";

export class PriceDetails extends Component {
    static template = "pos_self_order.PriceDetails";
    static props = { tax: Number, total: Number };
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
