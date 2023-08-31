/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";

export class AttributeSelection extends Component {
    static template = "pos_self_order.AttributeSelection";
    static props = ["product", "productState"];

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
            this.props.productState.showQtyButtons = true;
        }
    }

    prev() {
        if (this.state.currentAttribute !== 0) {
            this.state.currentAttribute--;
        }
    }

    attributeClicked() {
        if (this.state.editMode) {
            this.state.editMode = false;
            this.state.showResume = true;
            this.props.productState.showQtyButtons = true;
            return;
        }
        this.next();
    }

    editAttribute(attributeName) {
        const index = this.props.product.attributes.findIndex((a) => a.name === attributeName);
        this.state.showResume = false;
        this.state.editMode = true;
        this.state.currentAttribute = index;
        this.props.productState.showQtyButtons = false;
    }

    get attributeSelected() {
        let result = [];
        for (let [key, value] of Object.entries(this.props.productState.selectedVariants)){
            const attribute = this.props.productState.product.attributes.find(attribute => attribute.id===parseInt(key));
            const val = attribute.values.find(val => val.id === parseInt(value));
            result.push(
                {
                    name: attribute.name,
                    value: val.name,
                }
            )
        }
        return result;
    }
}
