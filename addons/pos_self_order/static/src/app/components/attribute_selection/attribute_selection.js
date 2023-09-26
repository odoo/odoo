/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { ProductCustomAttribute } from "@point_of_sale/app/store/models/product_custom_attribute";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { attributeFlatter, attributeFormatter } from "@pos_self_order/app/utils";

export class AttributeSelection extends Component {
    static template = "pos_self_order.AttributeSelection";
    static props = ["toggleQtyBtn", "product"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.numberOfAttributes = this.props.product.attributes.length;
        this.currentAttribute = 0;

        this.state = useState({
            currentAttribute: 0,
            editMode: false,
            showResume: false,
            showNext: false,
            showCustomInput: false,
        });

        this.selectedValues = useState(this.env.selectedValues);

        if (!this.env.editable) {
            this.state.showResume = true;
            this.props.toggleQtyBtn(true);
        }

        this.initAttribute();
    }

    get attribute() {
        return this.props.product.attributes[this.state.currentAttribute];
    }

    get availableAttributeValue() {
        return this.selfOrder.config.self_ordering_mode === "kiosk"
            ? this.attribute.values.filter((a) => !a.is_custom)
            : this.attribute.values;
    }

    get attributeSelected() {
        const flatAttribute = attributeFlatter(this.selectedValues);
        const customAttribute = this.env.customValues;
        return attributeFormatter(this.selfOrder.attributeById, flatAttribute, customAttribute);
    }

    initAttribute() {
        const attributeMulti = [];
        const attributeSingle = [];

        for (const attr of this.props.product.attributes) {
            if (attr.display_type !== "multi") {
                attributeSingle.push(attr);
            } else {
                attributeMulti.push(attr);
            }
        }

        for (const attribute of attributeSingle) {
            for (const value of attribute.values) {
                if (this.selfOrder.editedLine) {
                    if (this.selfOrder.editedLine.attribute_value_ids.includes(value.id)) {
                        this.selectedValues[attribute.id] = value.id;
                    }
                }

                if (value.is_custom) {
                    this.env.customValues[value.id] = new ProductCustomAttribute({
                        custom_product_template_attribute_value_id: value.id,
                    });
                }
            }
        }

        for (const attrMulti of attributeMulti) {
            this.selectedValues[attrMulti.id] = {};

            for (const value of attrMulti.values) {
                if (this.selfOrder.editedLine) {
                    if (this.selfOrder.editedLine.attribute_value_ids.includes(value.id)) {
                        this.selectedValues[attrMulti.id][value.id] = true;
                    }
                } else {
                    this.selectedValues[attrMulti.id][value.id] = false;
                }

                if (value.is_custom) {
                    this.env.customValues[value.id] = new ProductCustomAttribute({
                        custom_product_template_attribute_value_id: value.id,
                    });
                }
            }
        }
    }

    next() {
        this.state.showNext = false;
        this.state.showCustomInput = false;

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
        const currValue = this.selfOrder.attributeValueById[this.selectedValues[curAttr.id]];

        // not available in kiosk only in mobile mode
        if (currValue && currValue.is_custom) {
            this.state.showNext = true;
            this.state.showCustomInput = true;
            return;
        }

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

    isChecked(attribute, value) {
        return attribute.display_type === "multi"
            ? this.selectedValues[attribute.id][value.id]
            : parseInt(this.selectedValues[attribute.id]) === value.id;
    }
}
