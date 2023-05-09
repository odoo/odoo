/** @odoo-module */

import { Component, onWillStart } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { Order } from "@pos_self_order/Components/Order/Order";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { Loading } from "@pos_self_order/Components/Loading/Loading";
export class OrdersView extends Component {
    static template = "pos_self_order.OrdersView";
    static components = { Order, NavBar, Loading };
    static props = [];
    setup() {
        this.selfOrder = useSelfOrder();
        // this.selfOrder.updateOrders();
        onWillStart(async () => {
            this.selfOrder.updateOrders();
        });
    }
}
