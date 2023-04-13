/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product", "cartItem?", "currentProductCard?"];
    setup() {
        this.selfOrder = useSelfOrder();
        useForwardRefToParent("currentProductCard");
    }
    clickOnProduct(product) {
        if (
            this.selfOrder.table ||
            product.has_image ||
            product.description_sale ||
            product.attributes.length
        ) {
            this.env.navigate("/products/" + product.product_id);
        }
    }
}
