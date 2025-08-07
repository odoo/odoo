import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { floatIsZero } from "@web/core/utils/numbers";

export class ComboConfiguratorPopup extends Component {
    static template = "point_of_sale.ComboConfiguratorPopup";
    static components = { ProductCard, Dialog };
    static props = {
        productTemplate: Object,
        getPayload: Function,
        close: Function,
        line: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            combo: { ...this.props.line?.selectedComboIds } || {},
            configuration:
                this.props.line?.getAllLinesInCombo().reduce((acc, line) => {
                    if (!line.combo_item_id) {
                        return acc;
                    }

                    acc[line.combo_item_id.id] = {
                        attribute_value_ids: line.attribute_value_ids.map((a) => a.id),
                        price_extra: line.extra_price,
                        attribute_custom_values: line.custom_attribute_value_ids.reduce(
                            (acc, val) => {
                                acc[val.custom_product_template_attribute_value_id.id] =
                                    val.custom_value;
                                return acc;
                            },
                            {}
                        ),
                    };
                    return acc;
                }, {}) || {},
        });

        onMounted(() => {
            this.autoSelectSingleChoices();
            if (!this.hasMultipleChoices()) {
                this.confirm();
            }
        });
    }

    shouldShowCombo(combo) {
        return (
            combo.combo_item_ids.length > 0 &&
            (combo.combo_item_ids.length > 1 || combo.combo_item_ids[0].product_id.isConfigurable())
        );
    }

    autoSelectSingleChoices() {
        this.props.productTemplate.combo_ids.forEach((combo) => {
            if (
                combo.combo_item_ids.length === 1 &&
                !combo.combo_item_ids[0].product_id.isConfigurable()
            ) {
                this.state.combo[combo.id] = combo.combo_item_ids[0].id;
            }
        });
    }

    hasMultipleChoices() {
        return this.props.productTemplate.combo_ids.some((combo) => this.shouldShowCombo(combo));
    }

    areAllCombosSelected() {
        const values = Object.values(this.state.combo);
        return (
            values.length === this.props.productTemplate.combo_ids.length &&
            values.every((x) => Boolean(x))
        );
    }

    formattedComboPrice(comboItem) {
        const extra_price = comboItem.extra_price;
        if (floatIsZero(extra_price)) {
            return "";
        } else {
            const product = comboItem.product_id;
            const price = this.pos.getProductPrice(product, extra_price);
            return this.env.utils.formatCurrency(price);
        }
    }

    getSelectedComboItems() {
        return Object.values(this.state.combo)
            .filter((x) => x) // we only keep the non-zero values
            .map((x) => {
                const combo_item_id = this.pos.models["product.combo.item"].get(x);
                return {
                    combo_item_id: combo_item_id,
                    configuration: this.state.configuration[combo_item_id.id],
                };
            });
    }

    async onClickProduct({ product, combo_item }, ev) {
        const productTmpl = product.product_tmpl_id;
        if (productTmpl.needToConfigure()) {
            const allLines = this.props.line?.getAllLinesInCombo() || [];
            const line = allLines
                .filter((l) => l.combo_item_id)
                .find((l) => l.combo_item_id.id === combo_item.id);
            const payload = await this.pos.openConfigurator(product.product_tmpl_id, {
                hideAlwaysVariants: true,
                forceVariantValue: product.product_template_variant_value_ids,
                line,
                comboItem: combo_item,
            });
            if (payload) {
                this.state.configuration[combo_item.id] = payload;
            } else {
                this.state.combo[combo_item.combo_id.id] = 0;
            }
        }
    }

    confirm() {
        this.props.getPayload(this.getSelectedComboItems());
        this.props.close();
    }
}
