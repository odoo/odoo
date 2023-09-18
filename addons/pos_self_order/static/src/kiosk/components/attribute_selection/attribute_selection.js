/** @odoo-module */

import { useState } from "@odoo/owl";
import { AttributeSelector } from "@pos_self_order/common/components/attribute_selector/attribute_selector";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";

export class AttributeSelection extends AttributeSelector {
    static template = "pos_self_order.AttributeSelection";
    static props = ["toggleQtyBtn", ...AttributeSelector.props];

    setup() {
        this.selfOrder = useselfOrder();
        super.setup();
        this.numberOfAttributes = this.props.product.attributes.length;
        this.currentAttribute = 0;

        this.state = useState({
            ...this.state,
            currentAttribute: 0,
            editMode: false,
            showResume: false,
        });
    }

    get attribute() {
        return this.attributes[this.state.currentAttribute];
    }

    next() {
        if (this.state.currentAttribute !== this.numberOfAttributes - 1) {
            this.state.currentAttribute++;
        } else {
            this.state.showResume = true;
            this.props.toggleQtyBtn(true);
        }
    }

    prev() {
        if (this.state.currentAttribute !== 0) {
            this.state.currentAttribute--;
        }
    }

    attributeClicked() {
        const curAttr = this.attribute;

        if (this.state.editMode && curAttr.display_type !== "multi") {
            this.state.editMode = false;
            this.state.showResume = true;
            this.props.toggleQtyBtn(true);
            return;
        }

        if (curAttr && curAttr.display_type !== "multi") {
            this.next();
        }
    }

    editAttribute(id) {
        const index = this.props.product.attributes.findIndex((a) => a.id === id);
        this.state.showResume = false;
        this.state.editMode = true;
        this.state.currentAttribute = index;
        this.props.toggleQtyBtn(false);
    }
}
