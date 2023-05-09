/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { useForwardRefToParent } from "@web/core/utils/hooks";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product", "orderLine?", "currentProductCard?", "class?"];
    static defaultProps = { class: "" };
    setup() {
        this.selfOrder = useSelfOrder();
        useForwardRefToParent("currentProductCard");
        this.qtyInCart = !this.props.orderLine && this.qtyInCart();
    }
    clickOnProduct() {
        const product = this.props.product;
        if (!this.canOpenProductMainView(product)) {
            return;
        }
        if (this.selfOrder.page === "/cart") {
            this.selfOrder.setCurrentlyEditedOrderLine(this.props?.orderLine);
        }
        this.selfOrder.setPage("/products/" + product.product_id);
    }

    canOpenProductMainView(product) {
        return (
            this.selfOrder.table ||
            product.has_image ||
            product.description_sale ||
            product.attributes.length
        );
    }
    qtyInCart() {
        const cart = this.selfOrder.cart;
        const product = this.props.product;
        return cart
            .filter((x) => x.product_id === product.product_id)
            .reduce((sum, x) => sum + x.qty, 0);
    }
    getQtyInCartString() {
        return `${this.props.orderLine.qty} x ${this.selfOrder.formatMonetary(
            this.props.product.price_info.list_price +
                (this.props.orderLine?.price_extra.list_price || 0)
        )}`;
    }
    getTotalPriceString() {
        return `${this.selfOrder.formatMonetary(
            (this.props.orderLine?.qty || 1) *
                (this.props.product.price_info.list_price +
                    (this.props.orderLine?.price_extra.list_price || 0))
        )}`;
    }
}
