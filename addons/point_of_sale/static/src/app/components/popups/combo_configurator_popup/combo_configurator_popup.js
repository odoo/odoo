import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { QuantityButtons } from "@point_of_sale/app/components/buttons/quantity_buttons/quantity_buttons";
import { useService } from "@web/core/utils/hooks";

export class ComboConfiguratorPopup extends Component {
    static template = "point_of_sale.ComboConfiguratorPopup";
    static components = { ProductCard, Dialog, QuantityButtons };
    static props = {
        productTemplate: Object,
        getPayload: Function,
        close: Function,
        line: { type: Object, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");

        const selected = this.props.line?.getAllLinesInCombo()?.reduce((acc, value) => {
            if (!value.combo_item_id) {
                return acc;
            }

            acc[value.combo_item_id.id] = 1 + (acc[value.combo_item_id.id] || 0);
            return acc;
        }, {});

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
            qty: Object.fromEntries(
                this.props.productTemplate.combo_ids.map((combo) => [
                    combo.id,
                    Object.fromEntries(
                        combo.combo_item_ids.map((item) => [
                            item.id,
                            (selected && selected[item.id]) || 0,
                        ])
                    ),
                ])
            ),
        });

        onMounted(() => {
            this.autoSelectSingleChoices();
            if (!this.hasMultipleChoices()) {
                this.confirm();
            }
        });
    }

    shouldShowCombo(combo) {
        const items = combo.combo_item_ids;
        return items.length > 1 || combo.qty_max > 1 || items[0]?.product_id?.isConfigurable();
    }

    autoSelectSingleChoices() {
        this.props.productTemplate.combo_ids.forEach((combo) => {
            if (
                combo.combo_item_ids.length === 1 &&
                !combo.combo_item_ids[0].product_id.isConfigurable()
            ) {
                this.state.qty[combo.id][combo.combo_item_ids[0].id] = 1;
            }
        });
    }

    hasMultipleChoices() {
        return this.props.productTemplate.combo_ids.some((combo) => this.shouldShowCombo(combo));
    }

    isConfirmButtonEnabled() {
        return Object.keys(this.state.qty).every((comboId) => {
            const combo = this.pos.models["product.combo"].get(comboId);
            return combo.qty_free == 0 || this.totalQuantityForCombo(comboId) >= combo.qty_free;
        });
    }

    formattedComboPrice(comboItem) {
        return this.pos.currency.isZero(comboItem.extra_price)
            ? ""
            : this.env.utils.formatCurrency(comboItem.extra_price);
    }

    getSelectedComboItems() {
        const itemsIncluded = [];
        const itemsExtra = [];
        const comboFreeQtyTracker = {};
        Object.values(this.state.qty).forEach((comboItems) => {
            Object.entries(comboItems)
                .filter(([, qty]) => qty > 0)
                .forEach(([itemId, qty]) => {
                    const comboItemId = this.pos.models["product.combo.item"].get(itemId);
                    const comboId = comboItemId.combo_id.id;
                    const comboFreeQty = comboItemId.combo_id.qty_free;

                    if (!comboFreeQtyTracker[comboId]) {
                        comboFreeQtyTracker[comboId] = 0;
                    }

                    const remainingFreeQty = comboFreeQty - comboFreeQtyTracker[comboId];
                    if (remainingFreeQty > 0) {
                        const includedQty = Math.min(qty, remainingFreeQty);
                        itemsIncluded.push({
                            combo_item_id: comboItemId,
                            configuration: this.state.configuration[comboItemId.id],
                            qty: includedQty,
                        });
                        comboFreeQtyTracker[comboId] += includedQty;
                        qty -= includedQty;
                    }

                    if (qty > 0) {
                        itemsExtra.push({
                            combo_item_id: comboItemId,
                            configuration: this.state.configuration[comboItemId.id],
                            qty: qty,
                        });
                    }
                });
        });

        return [itemsIncluded, itemsExtra];
    }

    async onClickProduct(product, combo_item) {
        const productTmpl = product.product_tmpl_id;
        const combo = combo_item.combo_id;
        if (productTmpl.needToConfigure()) {
            this.onClickConfigurableProduct(product, combo_item, combo);
        } else {
            this.onClickSimpleProduct(combo_item, combo);
        }
    }

    resetSingleQtyMaxCombo(combo) {
        if (combo.qty_max === 1) {
            for (const itemId in this.state.qty[combo.id]) {
                this.state.qty[combo.id][itemId] = 0;
            }
        }
    }

    async onClickSimpleProduct(combo_item, combo) {
        this.resetSingleQtyMaxCombo(combo);
        if (this.totalQuantityForCombo(combo.id) < combo.qty_max) {
            this.state.qty[combo.id][combo_item.id] += 1;
        }
    }

    async onClickConfigurableProduct(product, combo_item, combo) {
        const isSingleQtyChoice = combo.qty_max === 1;
        if (this.totalQuantityForCombo(combo.id) < combo.qty_max || isSingleQtyChoice) {
            if (this.state.qty[combo.id][combo_item.id] > 0 && !isSingleQtyChoice) {
                this.state.qty[combo.id][combo_item.id] += 1;
            } else {
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
                    this.resetSingleQtyMaxCombo(combo);
                    this.state.configuration[combo_item.id] = payload;
                    this.state.qty[combo.id][combo_item.id] = 1;
                }
            }
        }
    }

    confirm() {
        this.props.getPayload(this.getSelectedComboItems());
        this.props.close();
    }

    showQuantityButtons(combo_item) {
        return (
            this.state.qty[combo_item.combo_id.id][combo_item.id] && combo_item.combo_id.qty_max > 1
        );
    }

    setQuantity(combo_item, quantity) {
        //Make sure quantity is within the bounds [0, combo_id.qty_max]
        const combo_id = combo_item.combo_id;
        const maxQtyAvailable =
            combo_id.qty_max -
            this.totalQuantityForCombo(combo_id.id) +
            this.state.qty[combo_id.id][combo_item.id];
        quantity = Math.max(0, Math.min(quantity, maxQtyAvailable));
        this.state.qty[combo_id.id][combo_item.id] = quantity;
    }

    totalQuantityForCombo(comboId) {
        return Object.values(this.state.qty[comboId]).reduce((total, qty) => total + qty, 0);
    }

    computeComboExtraPrice(combo) {
        const extraQty = this.totalQuantityForCombo(combo.id) - combo.qty_free;
        const extraQtyPrice = extraQty > 0 ? extraQty * combo.base_price : 0;

        const comboChoicesExtraPrices = combo.combo_item_ids.reduce((acc, comboItem) => {
            const qty = this.state.qty[combo.id][comboItem.id];
            const extraPrice = comboItem.extra_price;
            return acc + qty * extraPrice;
        }, 0);
        return extraQtyPrice + comboChoicesExtraPrices;
    }

    formatTotalPrice(productTemplate) {
        const basePrice = productTemplate.list_price;
        const extraPrice = productTemplate.combo_ids.reduce(
            (acc, combo) => acc + this.computeComboExtraPrice(combo),
            0
        );
        return this.env.utils.formatCurrency(basePrice + extraPrice);
    }

    getSelectedComboItemsText(combo) {
        return combo.qty_free > 1
            ? `${Math.min(this.totalQuantityForCombo(combo.id), combo.qty_free)}/${combo.qty_free}`
            : "1";
    }
}
