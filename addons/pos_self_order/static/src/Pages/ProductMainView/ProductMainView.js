/** @odoo-module */

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { FloatingButton } from "@pos_self_order/Components/FloatingButton/FloatingButton";
import { IncrementCounter } from "@pos_self_order/Components/IncrementCounter/IncrementCounter";
export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: Object };
    static components = {
        NavBar,
        FloatingButton,
        IncrementCounter,
    };
    setup() {
        this.selfOrder = useSelfOrder();
        this.main = useRef("main");
        onMounted(() => {
            // TODO: replace this logic with dvh once it is supported
            this.main.el.style.height = `${window.innerHeight}px`;
        });

        // we want to keep track of the last product that was viewed
        this.selfOrder.currentProduct = this.props.product.product_id;

        this.privateState = useState({
            // we look in the cart too see if the current product is already in it
            // if it is, we set the qty to the qty in the cart
            qty:
                this.selfOrder.cart.filter(
                    (item) => item.product_id === this.props.product.product_id
                )?.[0]?.qty || 1,
            customer_note: "",
            selectedVariants: Object.fromEntries(
                this.props.product.attributes.map((attribute) => [
                    attribute.name,
                    attribute.values[0].name,
                ])
            ),
        });
    }

    incrementQty = (up) => {
        if (up) {
            this.privateState.qty += 1;
            return;
        }
        if (this.privateState.qty >= 1) {
            this.privateState.qty -= 1;
        }
    };
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

    addToCartButtonClicked() {
        this.selfOrder.updateCart({
            product_id: this.selfOrder.currentProduct,
            qty: this.privateState.qty,
            customer_note: this.privateState.customer_note,
            description: Object.values(this.privateState.selectedVariants).join(", "),
            price_extra: this.getAllPricesExtra(
                this.privateState.selectedVariants,
                this.props.product.attributes
            ),
        });
        this.env.navigate("/products");
    }
}
