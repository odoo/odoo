/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { useForwardRefToParent, useService } from "@web/core/utils/hooks";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product", "line?", "currentProductCard?", "class?"];
    static defaultProps = { class: "" };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");

        useForwardRefToParent("currentProductCard");
    }

    get quantityInCart() {
        return this.selfOrder.currentOrder.lines?.reduce((sum, line) => {
            return line.product_id === this.props.product.id ? sum + line.qty : sum;
        }, 0);
    }

    clickOnProduct() {
        const product = this.props.product;
        this.router.navigate("product", { id: product.id });
    }

    getQtyInCartString() {
        // FIXME need to implement price_extra
        const productId = this.props.line.product_id;
        return `${this.props.line.qty} x ${this.selfOrder.productByIds[productId].prices}`;
    }
}
