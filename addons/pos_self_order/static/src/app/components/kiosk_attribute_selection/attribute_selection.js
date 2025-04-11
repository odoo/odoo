import { Component, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { AttributeSelectionHelper } from "./attribute_selection_helper";

export class KioskAttributeSelection extends Component {
    static template = "pos_self_order.KioskAttributeSelection";
    static props = ["productTemplate", "onSelection?"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.envSelectedValues = useState(this.env.selectedValues);
    }

    get selectedValues() {
        return (this.envSelectedValues[this.props.productTemplate.id] ??=
            new AttributeSelectionHelper());
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
