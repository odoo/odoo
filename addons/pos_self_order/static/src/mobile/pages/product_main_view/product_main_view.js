/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillUnmount, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { Product } from "@pos_self_order/common/models/product";
import { Line } from "@pos_self_order/common/models/line";
import { useService } from "@web/core/utils/hooks";
import { AttributeSelection } from "@pos_self_order/mobile/components/attribute_selection/attribute_selection";

export class ProductMainView extends Component {
    static template = "pos_self_order.ProductMainView";
    static props = { product: { type: Product, optional: true } };
    static components = {
        NavBar,
        AttributeSelection,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        useSubEnv({ attribute_components: [] });

        if (!this.props.product) {
            this.router.navigate("productList");
            return;
        }

        this.product = this.props.product;
        this.selfOrder.lastEditedProductId = this.product.id;
        this.state = useState({
            qty: 1,
            customer_note: "",
            cartQty: 0,
            selectedCombos: Object.fromEntries(
                this.product.pos_combo_ids?.map?.((id) => [
                    id,
                    this.selfOrder.comboByIds[id].combo_line_ids[0].id,
                ]) || []
            ),
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
        }

        return 0;
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
                _t("You cannot reduce the quantity of an order that has already been sent!"),
                { type: "danger" }
            );
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    orderlineCanBeMerged() {
        if (this.props.product.pos_combo_ids.length) {
            return false;
        }
        const editedLine = this.selfOrder.editedLine;

        if (editedLine) {
            return editedLine;
        }

        const line = this.selfOrder.currentOrder.lines.find(
            (l) =>
                JSON.stringify(l.selected_attributes.sort()) ===
                    JSON.stringify(this.env.attribute_components[0].selectedAttributeIds.sort()) &&
                l.customer_note === this.state.customer_note &&
                l.product_id === this.product.id
        );

        return line || false;
    }

    async addToCart() {
        const lines = this.selfOrder.currentOrder.lines;
        const lineToMerge = this.orderlineCanBeMerged();
        const selectedAttributes = this.env.attribute_components[0].selectedAttributeIds;

        if (lineToMerge) {
            const editedLine = this.selfOrder.editedLine;
            const gap = editedLine ? -1 : 0;

            lineToMerge.selected_attributes = selectedAttributes;
            lineToMerge.customer_note = this.state.customer_note;
            lineToMerge.qty += this.state.qty + gap;
        } else {
            const mainLine = new Line({
                id: lineToMerge ? lineToMerge.id : null,
                uuid: lineToMerge ? lineToMerge.uuid : null,
                qty: this.state.qty,
                product_id: this.product.id,
                customer_note: this.state.customer_note,
                selected_attributes: selectedAttributes,
            });
            lines.push(mainLine);
            for (const [combo_id, combo_line_id] of Object.entries(this.state.selectedCombos)) {
                const combo = this.selfOrder.comboByIds[combo_id];
                const combo_line = combo.combo_line_ids.find((l) => l.id == combo_line_id);
                const child_line = new Line({
                    qty: this.state.qty,
                    product_id: combo_line.product_id[0],
                    combo_parent_uuid: mainLine.uuid,
                    combo_id: combo.id,
                });
                lines.push(child_line);
                mainLine.child_lines.push(child_line);
            }
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
