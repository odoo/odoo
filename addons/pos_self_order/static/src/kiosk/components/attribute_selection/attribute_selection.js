/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";

export class AttributeSelection extends Component {
    static template = "pos_self_order.AttributeSelection";
    static props = ["product", "state"];

    setup() {
        this.selfOrder = useselfOrder();
        this.numberOfAttributes = this.props.product.attributes.length;
        this.currentAttribute = 0;

        this.state = useState({
            currentAttribute: 0,
            editMode: false,
            showResume: false,
        });
    }

    get attribute() {
        return this.props.product.attributes[this.state.currentAttribute];
    }

    next() {
        if (this.state.currentAttribute !== this.numberOfAttributes - 1) {
            this.state.currentAttribute++;
        } else {
            this.state.showResume = true;
            this.props.state.showQtyButtons = true;
        }
    }

    prev() {
        if (this.state.currentAttribute !== 0) {
            this.state.currentAttribute--;
        }
    }

    attributeClicked(attrId) {
        const curAttr = this.attribute;

        if (curAttr && curAttr.display_type === "multi") {
            if (!this.props.state.selectedVariants[curAttr.id]) {
                this.props.state.selectedVariants[curAttr.id] = new Set();
            }

            if (this.props.state.selectedVariants[curAttr.id].has(attrId)) {
                this.props.state.selectedVariants[curAttr.id].delete(attrId);
            } else {
                this.props.state.selectedVariants[curAttr.id].add(attrId);
            }
        }

        if (this.state.editMode && curAttr.display_type !== "multi") {
            this.state.editMode = false;
            this.state.showResume = true;
            this.props.state.showQtyButtons = true;
            return;
        }

        if (curAttr && curAttr.display_type !== "multi") {
            this.next();
        }
    }

    isChecked(attribute, value) {
        return (
            this.props.state.selectedVariants[attribute.id] instanceof Set &&
            this.props.state.selectedVariants[attribute.id].has(parseInt(value.id))
        );
    }

    editAttribute(id) {
        const index = this.props.product.attributes.findIndex((a) => a.id === id);
        this.state.showResume = false;
        this.state.editMode = true;
        this.state.currentAttribute = index;
        this.props.state.showQtyButtons = false;
    }

    get attributeSelected() {
        return Object.entries(this.props.state.selectedVariants).map(([key, value]) => {
            const attribute = this.selfOrder.attributeById[parseInt(key)];
            let valueName = "";

            if (value instanceof Set) {
                valueName = attribute.values
                    .filter((v) => value.has(v.id))
                    .map((v) => v.name)
                    .join(", ");
            } else {
                valueName = attribute.values.find((v) => v.id === parseInt(value)).name;
            }

            return {
                id: attribute.id,
                name: attribute.name,
                value: valueName,
            };
        });
    }
}
