/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { formatMonetary } from "@web/views/fields/formatters";
import { NavBar } from "@pos_self_order/NavBar/NavBar";
export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: Object };
    static components = {
        NavBar,
    };
    setup() {
        // we want to keep track of the last product that was viewed
        this.env.state.currentProduct = this.props.product.product_id;
        this.selfOrder = useSelfOrder();
        this.formatMonetary = formatMonetary;
    }
}

export default { ProductMainView };
