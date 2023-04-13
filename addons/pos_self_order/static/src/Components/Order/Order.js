/** @odoo-module */

import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { Component } from "@odoo/owl";
import { ProductCard } from "@pos_self_order/Components/ProductCard/ProductCard";
import { OrderLines } from "@pos_self_order/Components/OrderLines/OrderLines";
import { PriceDetails } from "@pos_self_order/Components/PriceDetails/PriceDetails";
export class Order extends Component {
    static template = "pos_self_order.Order";
    static components = { ProductCard, OrderLines, PriceDetails };
    static props = ["order"];
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
