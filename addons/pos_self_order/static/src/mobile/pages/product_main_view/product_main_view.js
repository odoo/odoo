/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";
import { NavBar } from "@pos_self_order/mobile/components/navbar/navbar";
import { Product } from "@pos_self_order/common/models/product";
import { Line } from "@pos_self_order/common/models/line";
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
            cartQty: 0,
            selectedCombos: Object.fromEntries(
                this.product.pos_combo_ids?.map?.((id) => [
                    id,
                    this.selfOrder.comboByIds[id].combo_line_ids[0].id,
                ]) || []
            ),
            /** this will be an object that will have the attribute id as key and the value id as value
             *  ex: selectedVariants: {4: 9, 5: 11} */
            selectedVariants: Object.fromEntries(
                this.product.attributes.map((att) => {
                    let selectedValue =
                        att.display_type == "multi" ? new Set() : att.values[0].id.toString();

                    if (this.selfOrder.editedLine) {
                        selectedValue = att.values
                            .filter((v) =>
                                Object.values(
                                    this.selfOrder.editedLine.selected_attributes
                                ).includes(v.id)
                            )
                            .map((v) => v.id);
                        selectedValue =
                            att.display_type == "multi"
                                ? new Set(selectedValue)
                                : selectedValue[0].toString();
                    }

                    return [att.id, selectedValue];
                })
            ),
        });

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });
    }
    getAttributeWithStringIds(attribute) {
        const values = attribute.values.map((value) => ({
            ...value,
            id: value.id.toString(),
        }));
        return { ...attribute, values };
    }
    updateMultipleAttribute(event, attributeId) {
        const value = parseInt(event.target.id);

        if (this.state.selectedVariants[attributeId].has(value)) {
            this.state.selectedVariants[attributeId].delete(value);
        } else {
            this.state.selectedVariants[attributeId].add(value);
        }
    }
    isChecked(attributeId, id) {
        return this.state.selectedVariants[attributeId].has(parseInt(id));
    }
    get disableAttributes() {
        const order = this.selfOrder.currentOrder;

        return (
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }

    get flattenSelectedAttribute() {
        return Object.values(this.state.selectedVariants)
            .map((value) => (value instanceof Set ? Array.from(value) : [parseInt(value)]))
            .flat();
    }
    get fullProductName() {
        if (!this.product.attributes.length) {
            return this.product.name;
        }

        const selectedAttributeString = this.flattenSelectedAttribute
            .map((attributeId) => this.selfOrder.attributeValueById[attributeId].name)
            .sort() // we need to keep same order each time to be able to compare
            .join(", ");

        return `${this.product.name} (${selectedAttributeString})`;
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
                l.full_product_name === this.fullProductName &&
                l.customer_note === this.state.customer_note &&
                l.product_id === this.product.id
        );

        return line || false;
    }

    async addToCart() {
        const lines = this.selfOrder.currentOrder.lines;
        const lineToMerge = this.orderlineCanBeMerged();

        if (lineToMerge) {
            const editedLine = this.selfOrder.editedLine;
            const gap = editedLine ? -1 : 0;

            lineToMerge.selected_attributes = this.flattenSelectedAttribute;
            lineToMerge.customer_note = this.state.customer_note;
            lineToMerge.full_product_name = this.fullProductName;
            lineToMerge.qty += this.state.qty + gap;
        } else {
            const mainLine = new Line({
                id: lineToMerge ? lineToMerge.id : null,
                uuid: lineToMerge ? lineToMerge.uuid : null,
                qty: this.state.qty,
                product_id: this.product.id,
                full_product_name: this.fullProductName,
                customer_note: this.state.customer_note,
                selected_attributes: this.flattenSelectedAttribute,
            });
            lines.push(mainLine);
            for (const [combo_id, combo_line_id] of Object.entries(this.state.selectedCombos)) {
                const combo = this.selfOrder.comboByIds[combo_id];
                const combo_line = combo.combo_line_ids.find((l) => l.id == combo_line_id);
                const child_line = new Line({
                    qty: this.state.qty,
                    product_id: combo_line.product_id[0],
                    full_product_name: this.selfOrder.productByIds[combo_line.product_id[0]].name,
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
