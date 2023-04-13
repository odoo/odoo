/** @odoo-module */

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { IncrementCounter } from "@pos_self_order/Components/IncrementCounter/IncrementCounter";
import { MainButton } from "@pos_self_order/Components/MainButton/MainButton";
export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: Object };
    static components = {
        NavBar,
        IncrementCounter,
        MainButton,
    };
    setup() {
        this.selfOrder = useSelfOrder();

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

    incrementQty(up) {
        this.orderLine.qty = this.computeNewQty(this.orderLine.qty, up);
    }
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
     * @param {import ("@pos_self_order/SelfOrderService").Attribute[]} attributes
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
        const getPriceExtra = (type) => this.getPriceExtra(selectedVariants, attributes, type);
        const priceTypes = ["list_price", "price_without_tax", "price_with_tax"];
        return Object.fromEntries(priceTypes.map((type) => [type, getPriceExtra(type)]));
    }

    preFormOrderline() {
        const orderLine = this.orderLine;
        const product = this.props.product;
        return {
            product_id: product.product_id,
            customer_note: orderLine.customer_note,
            description: Object.values(orderLine.selectedVariants).join(", "),
            nonFinalQty: orderLine.qty,
            price_extra: this.getAllPricesExtra(orderLine.selectedVariants, product.attributes),
        };
    }

    addToCartButtonClicked() {
        const preFormedOrderline = this.preFormOrderline();
        this.selfOrder.updateCart(preFormedOrderline);
        this.env.navigate(this.returnRoute());
    }
    returnRoute() {
        return this.selfOrder.currentlyEditedOrderLine ? "/cart" : "/products";
    }
}
