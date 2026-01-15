import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { AttributeSelectionHelper } from "./attribute_selection_helper";

export class AttributeSelection extends Component {
    static template = "pos_self_order.AttributeSelection";
    static props = ["productTemplate", "onSelection?"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.envSelectedValues = useState(this.env.selectedValues);
    }

    get selectedValues() {
        return (this.envSelectedValues[this.props.productTemplate.id] ??=
            new AttributeSelectionHelper(this.selfOrder));
    }

    isValueSelected(attribute, value) {
        return this.selectedValues.isValueSelected(attribute, value);
    }

    selectAttribute(attribute, value) {
        this.selectedValues.selectAttribute(attribute, value, this.props.onSelection);
    }

    availableAttributeValue(attribute) {
        return this.selfOrder.config.self_ordering_mode === "kiosk"
            ? attribute.product_template_value_ids.filter((a) => !a.is_custom)
            : attribute.product_template_value_ids;
    }

    getCustomSelectedValue(attribute) {
        if (attribute.attribute_id.display_type === "multi") {
            return null;
        }
        const valueId = this.selectedValues.getSelectedValue(attribute);
        if (!valueId) {
            return null;
        }

        const value = this.selfOrder.models["product.template.attribute.value"].get(valueId);
        if (value?.is_custom) {
            return value;
        }

        return null;
    }
    /*
    // TODO: Initialize attributes required for editing a line item
    initAttribute() {

        const initCustomValue = (value) => {
            const selectedValue = this.selfOrder.editedLine?.custom_attribute_value_ids.find(
                (v) => v.custom_product_template_attribute_value_id === value.id
            );

            return {
                custom_product_template_attribute_value_id: this.selfOrder.models[
                    "product.template.attribute.value"
                ].get(value.id),
                custom_value: selectedValue || "",
            };
        };

        const initValue = (value) => {
            if (this.selfOrder.editedLine?.attribute_value_ids.includes(value.id)) {
                return value.id;
            }
            return false;
        };

        for (const attr of this.props.productTemplate.attribute_line_ids) {
            this.selectedValues[attr.id] = {};

            for (const value of attr.product_template_value_ids) {
                if (attr.attribute_id.display_type === "multi") {
                    this.selectedValues[attr.id][value.id] = initValue(value);
                } else if (typeof this.selectedValues[attr.id] !== "number") {
                    this.selectedValues[attr.id] = initValue(value);
                }

                if (value.is_custom) {
                    this.env.customValues[value.id] = initCustomValue(value);
                }
            }
        }
    }*/

    shouldShowPriceExtra(value) {
        const priceExtra = value.price_extra;
        return !this.selfOrder.config.currency_id.isZero(priceExtra);
    }

    formatExtraPrice(value) {
        const priceExtra = value.price_extra;
        const sign = priceExtra < 0 ? "- " : "+ ";
        return sign + this.selfOrder.formatMonetary(Math.abs(priceExtra));
    }
}
