/** @odoo-module */

import { Component, onWillUnmount, useRef } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { useService, useForwardRefToParent } from "@web/core/utils/hooks";
import { Line } from "@pos_self_order/common/models/line";

export class ProductCard extends Component {
    static template = "pos_self_order.ProductCard";
    static props = ["product", "currentProductCard?"];

    selfRef = useRef("selfProductCard");
    currentProductCardRef = useRef("currentProductCard");

    setup() {
        this.selfOrder = useselfOrder();
        this.router = useService("router");
        this.cloneCard = null;

        useForwardRefToParent("currentProductCard");

        onWillUnmount(() => {
            if (this.cloneCard) {
                this.cloneCard.remove();
            }
        });
    }

    flyToCart() {
        const productCardEl = this.selfRef.el;
        if (!productCardEl) {
            return;
        }

        const cartButton = document.querySelector(".cart");
        if (!cartButton || window.getComputedStyle(cartButton).display === "none") {
            return;
        }

        if (this.cloneCard) {
            this.cloneCard.remove();
        }

        this.cloneCard = productCardEl.cloneNode(true);
        const cardRect = productCardEl.getBoundingClientRect();
        const cartRect = cartButton.getBoundingClientRect();

        this.cloneCard.style.position = "absolute";
        this.cloneCard.style.top = `${cardRect.top}px`;
        this.cloneCard.style.left = `${cardRect.left}px`;
        this.cloneCard.style.width = `${cardRect.width}px`;
        this.cloneCard.style.height = `${cardRect.height}px`;
        this.cloneCard.style.opacity = ".85";
        this.cloneCard.style.transition =
            "top 1s cubic-bezier(0.95, 0.1, 0.25, 0.95), left 1s cubic-bezier(0.95, 0.1, 0.25, 0.95), width 1s cubic-bezier(0.95, 0.1, 0.25, 0.95), height 1s cubic-bezier(0.95, 0.1, 0.25, 0.95), opacity 0.6s 0.2s ease-in-out";

        document.body.appendChild(this.cloneCard);

        requestAnimationFrame(() => {
            this.cloneCard.style.top = `${cartRect.top}px`;
            this.cloneCard.style.left = `${cartRect.left * 1.25}px`;
            this.cloneCard.style.width = `${cardRect.width * 0.8}px`;
            this.cloneCard.style.height = `${cardRect.height * 0.8}px`;
            this.cloneCard.style.opacity = "0"; // Fading out the card
        });

        this.cloneCard.addEventListener("transitionend", () => {
            this.cloneCard.remove();
        });
    }

    scaleUpPrice() {
        const priceElement = document.querySelector(".total-price");

        if (!priceElement) {
            return;
        }

        priceElement.classList.add("scale-up");

        setTimeout(() => {
            priceElement.classList.remove("scale-up");
        }, 600);
    }

    async addToCart() {
        const product = this.props.product;

        if (product.isCombo) {
            this.router.navigate("combo", { id: product.id });
        } else if (product.attributes.length > 0) {
            this.router.navigate("product", { id: product.id });
        } else {
            this.flyToCart();
            this.scaleUpPrice();

            const isProductInCart = this.selfOrder.currentOrder.lines.find(
                (line) => line.product_id === product.id
            );

            if (isProductInCart) {
                isProductInCart.qty++;
            } else {
                const lines = this.selfOrder.currentOrder.lines;

                lines.push(
                    new Line({
                        id: null,
                        uuid: null,
                        qty: 1,
                        product_id: product.id,
                        price_subtotal_incl: product.price_info.display_price,
                    })
                );
            }

            await this.selfOrder.getPricesFromServer();
        }
    }
}
