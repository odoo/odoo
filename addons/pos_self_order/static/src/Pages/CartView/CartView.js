/** @odoo-module */

import { Component, useEffect } from "@odoo/owl";
import { NavBar } from "@pos_self_order/Components/NavBar/NavBar";
import { ProductCard } from "@pos_self_order/Components/ProductCard/ProductCard";
import { OrderLines } from "@pos_self_order/Components/OrderLines/OrderLines";
import { useSelfOrder } from "@pos_self_order/SelfOrderService";
import { PriceDetails } from "@pos_self_order/Components/PriceDetails/PriceDetails";
import { MainButton } from "@pos_self_order/Components/MainButton/MainButton";

export class CartView extends Component {
    static components = { NavBar, ProductCard, OrderLines, PriceDetails, MainButton };
    static props = [];
    static template = "pos_self_order.CartView";
    setup() {
        this.selfOrder = useSelfOrder();
        useEffect(
            (cart) => {
                if (!cart.length) {
                    this.env.navigate("/products");
                }
            },
            () => [this.selfOrder.cart]
        );
    }
}
