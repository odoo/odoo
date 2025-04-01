import { Component, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { KioskAttributeSelection } from "@pos_self_order/app/components/kiosk_attribute_selection/attribute_selection";
import { KioskQuantityWidget } from "@pos_self_order/app/components/kiosk_quantity/quantity_widget";

export class KioskComboPage extends Component {
    static template = "pos_self_order.KioskComboPage";
    static props = ["productTemplate"];
    static components = { KioskAttributeSelection, KioskQuantityWidget };

    setup() {
        this.router = useService("router");
        if (!this.props.productTemplate) {
            this.router.navigate("product_list");
            return;
        }
        useSubEnv({ selectedValues: {} });
        this.selfOrder = useSelfOrder();
        this.state = useState({
            selectedChoiceIndex: 0,
            choices: [],
            showResume: false,
            qty: 1,
            selectedValues: this.env.selectedValues,
        });

        this.onAttributeSelection = this.onAttributeSelection.bind(this);
    }

    get currentCombo() {
        return this.props.productTemplate;
    }

    get selectedChoice() {
        return this.comboChoices[this.state.selectedChoiceIndex];
    }

    get comboChoices() {
        const combo = this.props.productTemplate.combo_ids;
        return combo.filter(
            (c) =>
                c.combo_item_ids.length > 1 ||
                (c.combo_item_ids.some((c) => c.product_id.attribute_line_ids.length !== 0) &&
                    !c.combo_item_ids.every((c) => c.product_id.isCombo()))
        );
    }

    get comboItems() {
        return this.selectedChoice.combo_item_ids;
    }

    get currentChoiceState() {
        return (this.state.choices[this.state.selectedChoiceIndex] ??= {});
    }

    selectItem(item) {
        const product = item.product_id;
        if (!product.self_order_available) {
            return;
        }

        if (!this.hasMultiItemSelection) {
            this.currentChoiceState.selectedItems = {};
        } else if (!this.canAddMoreItems()) {
            return;
        }

        const selectedItems = (this.currentChoiceState.selectedItems ||= {});

        if (selectedItems[item.id]) {
            // Already selected
            return;
        }

        const selection = (selectedItems[item.id] ||= { item });
        selection.item = item;
        selection.qty = 1;

        if (product.attribute_line_ids.length > 0) {
            this.currentChoiceState.displayAttributesOfItem = item;
        } else if (!this.hasMultiItemSelection) {
            this.next();
        }
    }

    getSelectedItems(choiceState = undefined) {
        if (!choiceState) {
            choiceState = this.currentChoiceState;
        }
        return Object.values((choiceState.selectedItems ||= {}));
    }

    getItemState(item) {
        const selection = this.currentChoiceState.selectedItems?.[item.id];
        if (!selection) {
            return { selected: false };
        }
        return { selected: true, qty: selection.qty };
    }

    get hasMultiItemSelection() {
        return this.selectedChoice.qty_max > 1;
    }

    canAddMoreItems() {
        return (
            this.getSelectedItems().reduce((sum, item) => sum + item.qty, 0) <
            this.selectedChoice.qty_max
        );
    }

    changeItemQuantity(item, value, evt) {
        evt.stopPropagation();
        evt.preventDefault();

        const itemState = this.currentChoiceState.selectedItems[item.id];
        if (!itemState) {
            return;
        }
        itemState.qty = Math.max(0, itemState.qty + value); // TODO: Check maximum allowed
        if (itemState.qty === 0) {
            delete this.currentChoiceState.selectedItems[item.id];
        }
    }

    isAttributeSelection() {
        return !!this.currentChoiceState.displayAttributesOfItem;
    }

    onAttributeSelection(singleSelection) {
        const product = this.currentChoiceState.displayAttributesOfItem.product_id;
        if (singleSelection && product.attribute_line_ids.length === 1) {
            this.next();
        }
    }

    isArchivedCombination() {
        if (!this.currentChoiceState.displayAttributesOfItem) {
            return false;
        }

        const comboItem = this.currentChoiceState.displayAttributesOfItem;
        if (!comboItem) {
            return false;
        }
        const selection = this.state.selectedValues[comboItem.product_id];
        if (!selection) {
            return false;
        }
        const variantAttributeValueIds = selection
            .getAllSelectedAttributeValuesIds()
            .map((attr) => Number(attr));
        return comboItem.product_id._isArchivedCombination(variantAttributeValueIds);
    }

    hasMissingAttributeValues(comboItem) {
        const product = comboItem.product_id;
        const selection = this.state.selectedValues[product.id];

        if (product.attribute_line_ids.length === 0) {
            return false;
        }
        if (!selection) {
            return true;
        }
        return selection.hasMissingAttributeValues(product.attribute_line_ids);
    }

    changeQuantity(increase) {
        if (!increase && this.state.qty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    isBackVisible() {
        return !(
            this.state.selectedChoiceIndex === 0 && !this.currentChoiceState.displayAttributesOfItem
        );
    }

    back() {
        if (this.state.showResume) {
            this.state.selectedChoiceIndex = this.comboChoices.length - 1;
            this.state.showResume = false;
            return;
        }

        if (this.isAttributeSelection()) {
            this.currentChoiceState.displayAttributesOfItem = false;
        } else {
            this.state.selectedChoiceIndex = Math.max(0, this.state.selectedChoiceIndex - 1);
        }
    }

    isNextEnabled() {
        if (this.currentChoiceState.displayAttributesOfItem) {
            const selectedItem = this.currentChoiceState.displayAttributesOfItem;
            if (!this.hasMissingAttributeValues(selectedItem) && !this.isArchivedCombination()) {
                return true;
            }
        } else {
            if (this.getSelectedItems().length > 0) {
                return true;
            }
        }
        return false;
    }

    next() {
        if (!this.isNextEnabled()) {
            return;
        }

        if (this.state.showResume) {
            this.addToCart();
            return;
        }

        const choices = this.comboChoices;
        const isLastChoice = this.state.selectedChoiceIndex === choices.length - 1;
        if (this.isAttributeSelection() || this.hasMultiItemSelection) {
            if (this.hasMultiItemSelection && this.isAttributeSelection()) {
                /// If we're in attribute selection for a multi-item choice, reset to item selection
                this.currentChoiceState.displayAttributesOfItem = false;
                return;
            }
        } else {
            const selectedItem = this.getSelectedItems()[0];
            if (selectedItem) {
                const hasAttributes = selectedItem.item.product_id.attribute_line_ids.length > 0;
                if (hasAttributes) {
                    this.currentChoiceState.displayAttributesOfItem = selectedItem;
                    return;
                }
            }
        }

        if (isLastChoice) {
            this.state.showResume = true;
        } else {
            this.state.selectedChoiceIndex += 1;
        }
    }

    onChoiceClicked(choiceIndex) {
        if (choiceIndex === this.state.selectedChoiceIndex) {
            this.state.showResume = false;
            this.currentChoiceState.displayAttributesOfItem = false;
            return;
        }

        // Ensure all previous choices are completed
        for (let i = 0; i < choiceIndex; i++) {
            const choice = this.state.choices[i];
            if (!choice) {
                return false;
            }
            //TODO optional selection
            const missingAttributes = this.getSelectedItems(choice).some((s) =>
                this.hasMissingAttributeValues(s.item)
            );
            if (missingAttributes) {
                return;
            }
        }

        this.state.showResume = false;
        this.state.selectedChoiceIndex = choiceIndex;
        this.currentChoiceState.displayAttributesOfItem = false;
    }

    getSelection() {
        return this.comboChoices.map((choice, index) => {
            const choiceState = this.state.choices[index];
            const comboItems = [];

            this.getSelectedItems(choiceState).forEach((itm) => {
                const comboItem = itm.item;
                const product = comboItem.product_id;
                const selectedAttributes = [];
                const productSelectedValues = this.state.selectedValues[product.id];

                product.attribute_line_ids.forEach((line) => {
                    const selection = productSelectedValues.getSelectedAttributeValues(line);

                    if (selection.length > 0) {
                        selectedAttributes.push({
                            attribute_line_id: line,
                            attribute_ids: selection,
                            names: selection.map((x) => x.name).join(", "),
                        });
                    }
                });

                comboItems.push({
                    combo_item_id: comboItem,
                    qty: itm.qty,
                    product_id: product,
                    attributes: selectedAttributes,
                });
            });

            return {
                combo_choice_id: choice,
                combo_items: comboItems,
            };
        });
    }

    addToCart() {
        const selectedCombos = [];
        this.getSelection().forEach((choice) => {
            choice.combo_items.forEach((item) => {
                const combo = {
                    combo_item_id: item.combo_item_id,
                    qty: item.qty,
                    configuration: {
                        attribute_custom_values: [],
                        attribute_value_ids:
                            item.attributes?.flatMap((s) => s.attribute_ids.map((x) => x.id)) || [],
                        price_extra: 0,
                    },
                };
                selectedCombos.push(combo);
            });
        });

        this.selfOrder.addToCart(
            this.props.productTemplate,
            this.state.qty,
            "",
            {},
            {},
            selectedCombos
        );
        this.router.back();
    }
}
