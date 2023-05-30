/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { ProductCard } from "@pos_self_order/components/product_card/product_card";
import { Lines } from "@pos_self_order/components/lines/lines";
import { PriceDetails } from "@pos_self_order/components/price_details/price_details";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { _t } from "@web/core/l10n/translation";

export class OrdersHistory extends Component {
    static template = "pos_self_order.OrdersHistory";
    static components = { NavBar, ProductCard, Lines, PriceDetails };
    static props = [];

    setup() {
        this.selfOrder = useSelfOrder();
        this.state = useState({
            loadingProgress: true,
        });

        this.loadOrder();
    }

    async loadOrder() {
        await this.selfOrder.getOrdersFromServer();
        this.state.loadingProgress = false;
    }

    get orders() {
        return this.selfOrder.orders.filter((o) => o.access_token);
    }

    editOrder(order) {
        if (this.selfOrder.self_order_mode === "meal" && order.state === "draft") {
            this.selfOrder.editedOrder = order;
            this.router.navigate("productList");
        } else {
            this.selfOrder.notification.add(_t("You cannot edit an posted order!"), {
                type: "danger",
            });
        }
    }
}
