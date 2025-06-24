import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductInfoBanner } from "@point_of_sale/app/components/product_info_banner/product_info_banner";

export class BaseProductAttribute extends Component {
    static template = "";
    static props = [
        "attribute",
        "selected",
        "setSelected",
        "customValue",
        "setCustomValue",
        "allSelectedValues",
    ];

    getFormatPriceExtra(val) {
        const sign = val < 0 ? "- " : "+ ";
        return sign + this.env.utils.formatCurrency(Math.abs(val));
    }
}

export class RadioProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.RadioProductAttribute";
}

export class PillsProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.PillsProductAttribute";
}

export class SelectProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.SelectProductAttribute";

    onChange(event) {
        this.props.setSelected(
            this.props.attribute.values().find((value) => value.id == event.target.value)
        );
    }
}

export class ColorProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.ColorProductAttribute";
}

export class MultiProductAttribute extends BaseProductAttribute {
    static template = "point_of_sale.MultiProductAttribute";

    setup() {
        this.state = useState({
            is_value_selected: this.props.attribute.values().reduce((acc, value) => {
                acc[value.id] = false;
                return acc;
            }, {}),
        });
    }

    onChange(value) {
        this.state.is_value_selected[value.id] = !this.state.is_value_selected[value.id];
        this.props.setSelected(
            this.props.attribute.values().filter((val) => this.state.is_value_selected[val.id])
        );
    }
}

export class ProductConfiguratorPopup extends Component {
    static template = "point_of_sale.ProductConfiguratorPopup";
    static components = {
        RadioProductAttribute,
        ProductInfoBanner,
        PillsProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
        MultiProductAttribute,
        Dialog,
    };
    static props = {
        productTemplate: Object,
        getPayload: Function,
        close: Function,
        hideAlwaysVariants: { type: Boolean, optional: true },
        forceVariantValue: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            attributes: this.props.productTemplate.attribute_line_ids.reduce((acc, attribute) => {
                acc[attribute.attribute_id.id] = {
                    selected: [],
                    custom_value: "",
                };
                return acc;
            }, {}),
        });

        this.initAttributes();
    }

    get attributes() {
        return this.props.productTemplate.attribute_line_ids;
    }

    get selectedValues() {
        return this.props.productTemplate.attribute_line_ids
            .map((attrLine) => this.state.attributes[attrLine.attribute_id.id]?.selected || [])
            .flat();
    }

    get product() {
        let product = null;
        const hasVariants = this.attributes.some(
            (line) => line.attribute_id.create_variant !== "no_variant"
        );

        if (hasVariants) {
            const selectedAttributeValuesIds = this.selectedValues.map(({ id }) => id);
            product = this.props.productTemplate.product_variant_ids.find(
                (product) =>
                    product.product_template_variant_value_ids?.length > 0 &&
                    product.product_template_variant_value_ids.every(({ id }) =>
                        selectedAttributeValuesIds.includes(id)
                    )
            );
        }
        return product;
    }

    initAttributes() {
        const getNext = this.generateCombinations(this.attributes);

        let combination;
        while ((combination = getNext()) !== null) {
            if (!combination.some((value) => value.doHaveConflictWith(combination))) {
                combination.forEach((value) => {
                    const forceVariant = this.props.forceVariantValue
                        ? Object.values(this.props.forceVariantValue).find(
                              (att) => att.attribute_line_id.id == value.attribute_line_id.id
                          )
                        : false;
                    this.state.attributes[value.attribute_id.id].selected = forceVariant || value;
                });
                break;
            }
        }
    }

    generateCombinations(attributes) {
        const values = attributes
            .filter(({ attribute_id }) => attribute_id.display_type !== "multi")
            .map((attribute) => attribute.values());
        const indices = new Array(values.length).fill(0);
        let done = false;

        return function getNextCombination() {
            if (done) {
                return null;
            }
            const combination = indices.map((idx, i) => values[i][idx]);

            for (let i = values.length - 1; i >= 0; i--) {
                if (indices[i] < values[i].length - 1) {
                    indices[i]++;
                    break;
                } else {
                    indices[i] = 0;
                    if (i === 0) {
                        done = true;
                    }
                }
            }

            return combination;
        };
    }

    setSelected(attribute) {
        return (selected) => {
            this.state.attributes[attribute.attribute_id.id].selected = selected;
        };
    }

    setCustomValue(attribute) {
        return (custom_value) => {
            this.state.attributes[attribute.attribute_id.id].custom_value = custom_value;
        };
    }

    computePayload() {
        return {
            attribute_value_ids: this.selectedValues.map((val) => val.id),
            attribute_custom_values: Object.values(this.state.attributes)
                .filter((attribute) => attribute.selected.is_custom)
                .reduce((acc, { selected, custom_value }) => {
                    acc[selected.id] = custom_value;
                    return acc;
                }, []),
            price_extra: this.selectedValues
                .filter((value) => value.attribute_id.create_variant === "no_variant")
                .reduce((acc, val) => acc + val.price_extra, 0),
        };
    }

    isArchivedCombination() {
        const selectedValuesIds = this.selectedValues
            .filter((value) => value.attribute_id.create_variant === "always")
            .map(({ id }) => id);
        return (
            selectedValuesIds.length > 0 &&
            this.props.productTemplate._isArchivedCombination(selectedValuesIds)
        );
    }

    get title() {
        const info = this.props.productTemplate.getProductPriceInfo(this.product, this.pos.company);
        const name = this.props.productTemplate.display_name;
        const total = this.env.utils.formatCurrency(info?.raw_total_included_currency || 0.0);
        const taxName = info?.taxes_data[0]?.name || "";
        const taxAmount = this.env.utils.formatCurrency(
            info?.taxes_data[0]?.raw_tax_amount_currency || 0.0
        );
        return `${name} | ${total} | VAT: ${taxName} (= ${taxAmount})`;
    }
    get showInfoBanner() {
        return this.props.productTemplate.is_storable;
    }
    close() {
        this.props.close();
    }

    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }

    get validAttributeLineIds() {
        if (this.props.hideAlwaysVariants) {
            return this.props.productTemplate.attribute_line_ids.filter(
                (line) => line.attribute_id.create_variant !== "always"
            );
        } else {
            return this.props.productTemplate.attribute_line_ids;
        }
    }
}
