/** @odoo-module */

import { Component, useExternalListener } from "@odoo/owl";

export class ProductInfoPopup extends Component {
    static template = "pos_self_order.ProductInfoPopup";
    static props = ["product", "addToCart"];

    setup() {
        useExternalListener(window, "click", this.props.close);
    }

    addToCartAndClose() {
        this.props.addToCart();
        this.props.close();
    }
}
