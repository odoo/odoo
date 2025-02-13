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
    static props = ["productTemplate", "getPayload", "close"];

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
        return Object.values(this.state.attributes)
            .map((attribute) => attribute.selected)
            .flat();
    }

    get product() {
        const alwaysVariants = this.attributes.every(
            (line) => line.attribute_id.create_variant === "always"
        );

        if (alwaysVariants) {
            const selectedAttributeValuesIds = this.selectedValues.map(({ id }) => id);
            const product = this.pos.models["product.product"].find(
                (product) =>
                    product.product_template_variant_value_ids?.length > 0 &&
                    product.product_template_variant_value_ids.every(({ id }) =>
                        selectedAttributeValuesIds.includes(id)
                    )
            );
            return product ? product : this.pos.models["product.product"];
        }

        return this.pos.models["product.product"];
    }

    initAttributes() {
        const getNext = this.generateCombinations(this.attributes);

        let combination;
        while ((combination = getNext()) !== null) {
            if (!combination.some((value) => value.doHaveConflictWith(combination))) {
                combination.forEach((value) => {
                    this.state.attributes[value.attribute_id.id].selected = value;
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

    close() {
        this.props.close();
    }

    confirm() {
        this.props.getPayload(this.computePayload());
        this.props.close();
    }
}

export class OptionalProductLine extends ProductConfiguratorPopup {
    static template = "point_of_sale.OptionalProductLine";
    static components = {
        RadioProductAttribute,
        PillsProductAttribute,
        SelectProductAttribute,
        ColorProductAttribute,
        MultiProductAttribute,
    };

    static props = ["productTemplate", "isButtonDisable"];

    setup() {
        super.setup();
        this.state = useState({
            ...this.state,
            qty: 0,
        });

        onMounted(() => {
            this.env.product_lines.push(this);
            this.computeProductProduct();
        });
    }
    changeQuantity(increase) {
        this.state.qty += increase ? 1 : -1;
        this.props.isButtonDisable();
    }
    onInputChangeQuantity(quantity) {
        quantity = parseInt(quantity);
        this.state.qty = quantity >= 0 ? quantity : 0;
        this.props.isButtonDisable();
    }

    async getValue() {
        const values = {
            product_tmpl_id: this.props.productTemplate,
            product_id: this.state.product || this.props.productTemplate.product_variant_ids[0],
            qty: this.state.qty,
            price_extra: 0,
        };
        const configurableData = await this.pos.processConfigurableData(
            this.computePayload(),
            values,
            this.props.productTemplate
        );
        Object.assign(values, configurableData);
        return values;
    }
}

export class OptionalProductPopup extends Component {
    static template = "point_of_sale.OptionalProductPopup";
    static components = {
        OptionalProductLine,
        Dialog,
    };

    static props = ["close", "productTemplate"];

    setup() {
        useSubEnv({
            product_lines: [],
        });
        this.pos = usePos();
        this.state = useState({
            payload: this.env.product_lines,
            buttonDisabled: true,
        });
    }
    cancel() {
        this.props.close();
    }
    isButtonDisable() {
        this.state.buttonDisabled = !this.state.payload.some((line) => line.state.qty);
    }
    confirm() {
        this.state.payload.forEach(async (payload) => {
            const payloadVlaue = await payload.getValue();
            const configure = payloadVlaue.product_tmpl_id.isCombo() ? true : false;
            if (payloadVlaue.qty > 0) {
                await this.pos.addLineToCurrentOrder(payloadVlaue, {}, configure);
            }
            if (payloadVlaue.product_tmpl_id.isCombo()) {
                for (const line of this.pos.getOrder().getSelectedOrderline().combo_line_ids) {
                    line.setQuantity(payloadVlaue.qty, true);
                }
            }
        });
        this.props.close();
    }
}
