/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { ProductCard } from "@pos_self_order/mobile/components/product_card/product_card";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { useService } from "@web/core/utils/hooks";

export class OrdersHistory extends Component {
    static template = "pos_self_order.OrdersHistory";
    static components = { NavBar, ProductCard, OrderWidget, Orderline };
    static props = [];

    async setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.state = useState({
            loadingProgress: true,
        });

        await this.loadOrder();
    }

    async loadOrder() {
        await this.selfOrder.getOrdersFromServer();
        this.state.loadingProgress = false;
    }

    get orders() {
        return this.selfOrder.orders.filter((o) => o.access_token).sort((a, b) => b.id - a.id);
    }

    editOrder(order) {
        if (order.state === "draft") {
            this.selfOrder.editedOrder = order;
            this.router.navigate("productList");
        }
    }
}
