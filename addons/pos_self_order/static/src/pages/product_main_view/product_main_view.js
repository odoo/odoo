/** @odoo-module */

import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { NavBar } from "@pos_self_order/components/navbar/navbar";
import { Product } from "../../models/product";
import { Line } from "../../models/line";
import { useService } from "@web/core/utils/hooks";

export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: { type: Product, optional: true } };
    static components = {
        NavBar,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");

        if (!this.props.product) {
            this.router.navigate("productList");
            return;
        }

        this.product = this.props.product;
        this.selfOrder.lastEditedProductId = this.product.id;
        this.state = useState({
            qty: 1,
            customer_note: "",
            selectedVariants: [],
            cartQty: 0,
        });

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });

        this.initState();
    }

    initState() {
        const editedLine = this.selfOrder.editedLine;

        if (editedLine) {
            this.state.customer_note = editedLine.customer_note;
            this.state.cartQty = editedLine.qty - 1;

            if (editedLine.selected_attributes) {
                this.state.selectedVariants = editedLine.selected_attributes;
            }
        } else {
            this.state.selectedVariants = this.product.attributes.reduce((acc, curr) => {
                acc[curr.name] = curr.values[0].name;
                return acc;
            }, {});
        }

        return 0;
    }

    get fullProductName() {
        const productAttributeString = Object.values(this.state.selectedVariants).join(", ");
        let name = `${this.product.name}`;

        if (productAttributeString) {
            name += ` (${productAttributeString})`;
        }

        return name;
    }

    changeQuantity(increase) {
        const currentQty = this.state.qty + this.state.cartQty;
        const lastOrderSent = this.selfOrder.currentOrder.lastChangesSent;
        const sentQty = lastOrderSent[this.selfOrder.editedLine?.uuid]?.qty;

        if (!increase && currentQty === 0) {
            return;
        }

        if (!increase && sentQty === currentQty) {
            this.selfOrder.notification.add(
                this.env._t(
                    "You cannot reduce the quantity of an order that has already been sent!"
                ),
                { type: "danger" }
            );
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    orderlineCanBeMerged(newLine) {
        const editedLine = this.selfOrder.editedLine;

        if (editedLine) {
            return editedLine;
        }

        const line = this.selfOrder.currentOrder.lines.find(
            (l) =>
                l.full_product_name === this.fullProductName &&
                l.customer_note === this.state.customer_note &&
                l.product_id === this.product.id
        );

        return line ? line : false;
    }

    async addToCart() {
        const lines = this.selfOrder.currentOrder.lines;
        const lineToMerge = this.orderlineCanBeMerged();

        if (lineToMerge) {
            const editedLine = this.selfOrder.editedLine;
            const gap = editedLine ? -1 : 0;

            lineToMerge.selected_attributes = this.state.selectedVariants;
            lineToMerge.customer_note = this.state.customer_note;
            lineToMerge.full_product_name = this.fullProductName;
            lineToMerge.qty += this.state.qty + gap;
        } else {
            lines.push(
                new Line({
                    id: lineToMerge ? lineToMerge.id : null,
                    uuid: lineToMerge ? lineToMerge.uuid : null,
                    qty: this.state.qty,
                    product_id: this.product.id,
                    full_product_name: this.fullProductName,
                    customer_note: this.state.customer_note,
                    selected_attributes: this.state.selectedVariants,
                })
            );
        }

        // If a command line does not have a quantity greater than 0, we consider it deleted
        await this.selfOrder.getPricesFromServer();
        this.selfOrder.currentOrder.lines = lines.filter((o) => o.qty > 0);

        if (this.selfOrder.currentOrder.lines.length === 0) {
            this.router.navigate("productList");
        } else {
            this.router.back();
        }
    }
}
