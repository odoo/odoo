/** @odoo-module */

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { IncrementCounter } from "@pos_self_order/Components/IncrementCounter/IncrementCounter";
export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: Object };
    static components = {
        NavBar,
        IncrementCounter,
    };
    setup() {
        this.selfOrder = useSelfOrder();
        this.main = useRef("main");
        onMounted(() => {
            this.main.el.style.height = `${window.innerHeight}px`;
        });

        onWillUnmount(() => {
            this.selfOrder.currentlyEditedOrderLine = null;
        });

        // we want to keep track of the last product that was viewed
        this.selfOrder.currentProduct = this.props.product.product_id;
        this.orderLine = useState({
            qty: this.selfOrder?.currentlyEditedOrderLine?.qty || 1,
            customer_note: this.selfOrder?.currentlyEditedOrderLine?.customer_note || "",
            selectedVariants: Object.fromEntries(
                this.props.product.attributes.map((attribute, key) => [
                    attribute.name,
                    this.selfOrder?.currentlyEditedOrderLine?.description?.split(", ")?.[key] ||
                        attribute.values[0].name,
                ])
            ),
        });
    }

    incrementQty = (up) => {
        this.orderLine.qty = this.computeNewQty(this.orderLine.qty, up);
    };
    computeNewQty(qty, up) {
        if (up) {
            return qty + 1;
        }
        if (qty > 1) {
            return qty - 1;
        }
        if (this.selfOrder.currentlyEditedOrderLine) {
            return 0;
        }
        return 1;
    }
    /**
     * @param {Object} selectedVariants
     * @param {[]} attributes
     * @param {"list_price" | "price_with_tax" | "price_without_tax"} type
     * @returns {Number}
     */
    getPriceExtra(selectedVariants, attributes, type = "list_price") {
        return (
            Object.entries(selectedVariants).reduce((sum, selected) => {
                return (
                    sum +
                    attributes
                        .find((attribute) => attribute.name == selected[0])
                        .values.find((value) => value.name == selected[1]).price_extra[type]
                );
            }, 0) || 0
        );
    }
    getAllPricesExtra(selectedVariants, attributes) {
        return {
            list_price: this.getPriceExtra(selectedVariants, attributes, "list_price"),
            price_without_tax: this.getPriceExtra(
                selectedVariants,
                attributes,
                "price_without_tax"
            ),
            price_with_tax: this.getPriceExtra(selectedVariants, attributes, "price_with_tax"),
        };
    }
    /**
     * The selfOrder.updateCart method expects us to give it the
     * total qty the orderline should have.
     * If we are currently editing an existing orderline ( that means that we came to this
     * page from the cart page), it means that we are editing the total qty itself,
     * so we just return orderLine.qty.
     * If we came to this page from the products page, it means that we are adding items,
     * so we need to add the qty of the current product to the qty that is
     * already in the cart.
     */
    findQty() {
        return this.orderLine.qty && (this.findMergeableOrderLine()?.qty || 0) + this.orderLine.qty;
    }
    findMergeableOrderLine() {
        return this.selfOrder.cart.find((item) =>
            this.selfOrder.canBeMerged(item, this.preFormOrderline())
        );
    }

    preFormOrderline() {
        return {
            product_id: this.props.product.product_id,
            customer_note: this.orderLine.customer_note,
            description: Object.values(this.orderLine.selectedVariants).join(", "),
        };
    }

    formOrderLine() {
        return {
            ...this.preFormOrderline(),
            qty: this.findQty(),
            price_extra: this.getAllPricesExtra(
                this.orderLine.selectedVariants,
                this.props.product.attributes
            ),
        };
    }

    addToCartButtonClicked() {
        // if we are editing an orderline, instead of trying to change the existing orderline
        // we delete it and add a new one
        this.selfOrder.deleteOrderLine(this.selfOrder.currentlyEditedOrderLine);
        this.selfOrder.updateCart(this.formOrderLine());
        this.selfOrder.setPage(this.returnRoute());
    }
    returnRoute() {
        return this.selfOrder.currentlyEditedOrderLine ? "/cart" : "/products";
    }
}
