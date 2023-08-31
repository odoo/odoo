/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { ProductCard } from "@pos_self_order/mobile/components/product_card/product_card";
import { Lines } from "@pos_self_order/mobile/components/lines/lines";
import { PriceDetails } from "@pos_self_order/mobile/components/price_details/price_details";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { useService } from "@web/core/utils/hooks";

export class OrdersHistory extends Component {
    static template = "pos_self_order.OrdersHistory";
    static components = { NavBar, ProductCard, Lines, PriceDetails };
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
