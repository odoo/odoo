/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { Order } from "@pos_self_order/Components/Order/Order";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
export class OrdersView extends Component {
    static template = "pos_self_order.OrdersView";
    static components = { Order, NavBar };
    static props = [];
    setup() {
        this.selfOrder = useSelfOrder();
        onWillStart(async () => {
            this.selfOrder.orders = await this.selfOrder.getUpdatedOrdersFromServer(
                this.selfOrder.orders
            );
        });
    }
}
