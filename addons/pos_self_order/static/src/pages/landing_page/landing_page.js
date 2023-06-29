/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
export class LandingPage extends Component {
    static template = "pos_self_order.LandingPage";
    static props = [];
    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.formatMonetary = formatMonetary;
        this.selfOrder.currentProduct = 0;
    }

    showMyOrderBtn() {
        const ordersNotDraft = this.selfOrder.orders.find((o) => o.access_token);
        return this.selfOrder.ordering && ordersNotDraft;
    }
}
