/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { ProductCard } from "../ProductCard/ProductCard";

export class OrderLines extends Component {
    static template = "pos_self_order.OrderLines";
    static components = { ProductCard };
    static props = ["lines"];
    setup() {
        this.selfOrder = useSelfOrder();
    }
    formatProduct(product) {
        return (({ description_sale, has_image, ...rest }) => ({ has_image: false, ...rest }))(
            product
        );
    }
}
