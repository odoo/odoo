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
            showResume: false,
            showNext: false,
            showCustomInput: false,
        });

        this.selectedValues = useState(this.env.selectedValues);

        if (!this.env.editable) {
            this.toggleResume();
        }

        this.initAttribute();
    }

    get showNextBtn() {
        for (const attrSelection of Object.values(this.selectedValues)) {
            if (!attrSelection) {
                return false;
            }
        }

        return true;
    }

    get attributeSelected() {
        const flatAttribute = attributeFlatter(this.selectedValues);
        const customAttribute = this.env.customValues;
        return attributeFormatter(this.selfOrder.attributeById, flatAttribute, customAttribute);
    }

    availableAttributeValue(attribute) {
        return this.selfOrder.config.self_ordering_mode === "kiosk"
            ? attribute.values.filter((a) => !a.is_custom)
            : attribute.values;
    }

    initAttribute() {
        const initCustomValue = (value) => {
            let selectedValue = this.selfOrder.editedLine?.custom_attribute_value_ids.find(
                (v) => v.custom_product_template_attribute_value_id === value.id
            );

            if (!selectedValue) {
                selectedValue = new ProductCustomAttribute({
                    custom_product_template_attribute_value_id: value.id,
                });
            }

            return selectedValue;
        };

        const initValue = (value) => {
            if (this.selfOrder.editedLine?.attribute_value_ids.includes(value.id)) {
                return value.id;
            }
            return false;
        };

        for (const attr of this.props.product.attributes) {
            this.selectedValues[attr.id] = {};

            for (const value of attr.values) {
                if (attr.display_type === "multi") {
                    this.selectedValues[attr.id][value.id] = initValue(value);
                } else if (typeof this.selectedValues[attr.id] !== "number") {
                    this.selectedValues[attr.id] = initValue(value);
                }

                if (value.is_custom) {
                    this.env.customValues[value.id] = initCustomValue(value);
                }
            }
        }
    }

    toggleResume() {
        this.state.showResume = !this.state.showResume;
        this.props.toggleQtyBtn(this.state.showResume);
    }

    isChecked(attribute, value) {
        return attribute.display_type === "multi"
            ? this.selectedValues[attribute.id][value.id]
            : parseInt(this.selectedValues[attribute.id]) === value.id;
    }
}
