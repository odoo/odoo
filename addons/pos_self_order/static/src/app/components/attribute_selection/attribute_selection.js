import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { attributeFlatter, attributeFormatter } from "@pos_self_order/app/utils";
import { floatIsZero } from "@web/core/utils/numbers";

export class AttributeSelection extends Component {
    static template = "pos_self_order.AttributeSelection";
    static props = ["product"];

    setup() {
        this.selfOrder = useSelfOrder();
        this.numberOfAttributes = this.props.product.attribute_line_ids.length;
        this.currentAttribute = 0;

        this.gridsRef = {};
        this.valuesRef = {};
        for (const attr of this.props.product.attribute_line_ids) {
            this.gridsRef[attr.id] = useRef(`attribute_grid_${attr.id}`);
            this.valuesRef[attr.id] = {};
            for (const value of attr.product_template_value_ids) {
                this.valuesRef[attr.id][value.id] = useRef(`value_${attr.id}_${value.id}`);
            }
        }

        this.state = useState({
            showNext: false,
            showCustomInput: false,
        });

        this.selectedValues = useState(this.env.selectedValues);

        this.initAttribute();
        onMounted(this.onMounted);
    }

    onMounted() {
        for (const attr of Object.entries(this.valuesRef)) {
            let classicValue = 0;
            for (const valueRef of Object.values(attr[1])) {
                if (valueRef.el) {
                    const height = valueRef.el.parentNode.offsetHeight;
                    if (classicValue === 0) {
                        classicValue = height;
                    } else {
                        if (height !== classicValue || height > window.innerHeight * 0.18) {
                            this.gridsRef[attr[0]].el.classList.remove(
                                "row-cols-2",
                                "row-cols-sm-3",
                                "row-cols-md-4",
                                "row-cols-xl-5",
                                "row-cols-xxl-6"
                            );
                            this.gridsRef[attr[0]].el.classList.add("row-cols-1");
                            for (const gridValueRef of Object.values(attr[1])) {
                                gridValueRef.el.classList.remove("ratio", "ratio-16x9");
                            }
                            break;
                        }
                    }
                }
            }
        }
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
        return attributeFormatter(
            this.selfOrder.models["product.attribute"].getAllBy("id"),
            flatAttribute,
            customAttribute
        );
    }

    availableAttributeValue(attribute) {
        return this.selfOrder.config.self_ordering_mode === "kiosk"
            ? attribute.product_template_value_ids.filter((a) => !a.is_custom)
            : attribute.product_template_value_ids;
    }

    availableAttributes() {
        return this.props.product.attribute_line_ids.filter(
            (a) => a.attribute_id.create_variant !== "always"
        );
    }

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

        for (const attr of this.availableAttributes()) {
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
    }

    isChecked(attribute, value) {
        return attribute.attribute_id.display_type === "multi"
            ? this.selectedValues[attribute.id][value.id]
            : parseInt(this.selectedValues[attribute.id]) === value.id;
    }

    shouldShowPriceExtra(value) {
        const priceExtra = value.price_extra;
        return !floatIsZero(priceExtra, this.selfOrder.config.currency_decimals);
    }

    getfPriceExtra(value) {
        const priceExtra = value.price_extra;
        const sign = priceExtra < 0 ? "- " : "+ ";
        return sign + this.selfOrder.formatMonetary(Math.abs(priceExtra));
    }
}
