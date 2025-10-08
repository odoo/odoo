import { Component, onWillUnmount, useState, useSubEnv, useRef, onMounted } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { AttributeSelection } from "@pos_self_order/app/components/attribute_selection/attribute_selection";
import { ProductNameWidget } from "@pos_self_order/app/components/product_name_widget/product_name_widget";
import { ComboStepper } from "@pos_self_order/app/components/combo_stepper/combo_stepper";
import { computeTotalComboPrice } from "../../services/card_utils";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";

export class ComboPage extends Component {
    static template = "pos_self_order.ComboPage";
    static props = ["productTemplate"];
    static components = {
        AttributeSelection,
        ComboStepper,
        ProductNameWidget,
    };

    setup() {
        this.router = useService("router");
        if (!this.props.productTemplate) {
            this.goBack();
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
            comboPrice: 0,
            topShadowOpacity: 0,
            bottomShadowOpacity: 1,
        });
        this.onAttributeSelection = this.onAttributeSelection.bind(this);

        this.productNameRef = useRef("productName");
        this.scrollContainerRef = useRef("scrollContainer");
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);

        onMounted(() => {
            const productNameEl = this.productNameRef.el;
            if (productNameEl) {
                this.observer = new IntersectionObserver(
                    ([entry]) => {
                        this.state.showStickyTitle = !entry.isIntersecting;
                    },
                    {
                        root: null,
                        threshold: 0,
                    }
                );
                this.observer.observe(productNameEl);
            }
            this.resetScrollPosition();
        });

        onWillUnmount(() => {
            if (this.observer) {
                this.observer.unobserve(this.productNameRef.el);
            }
        });
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
                c.qty_max > 1 ||
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

    shouldShowMissingDetails() {
        const el = this.scrollContainerRef?.el;
        if (!el) {
            return false;
        }
        return (
            el.scrollHeight > el.clientHeight &&
            this.currentChoiceState.displayAttributesOfItem.product_id.attribute_line_ids.length > 1
        );
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
            this.changeItemQuantity(null, item, +1);
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
        return this.getSelectedItemCount() < this.selectedChoice.qty_max;
    }

    getSelectedItemCount() {
        return this.getSelectedItems().reduce((sum, item) => sum + item.qty, 0);
    }

    get hasSelectedItems() {
        return this.getSelectedItems().some((item) => item.qty > 0);
    }

    changeItemQuantity(evt, item, value) {
        evt?.stopPropagation();

        if (value > 0 && !this.canAddMoreItems()) {
            return;
        }
        const itemState = this.currentChoiceState.selectedItems[item.id];
        if (!itemState) {
            return;
        }
        itemState.qty = Math.max(0, itemState.qty + value);
        if (itemState.qty === 0) {
            delete this.currentChoiceState.selectedItems[item.id];
        }
    }

    isAttributeSelection() {
        return !!this.currentChoiceState.displayAttributesOfItem;
    }

    onAttributeSelection(singleSelection, attribute, value) {
        const product = this.currentChoiceState.displayAttributesOfItem.product_id;
        if (singleSelection && product.attribute_line_ids.length === 1) {
            if (!this.selfOrder.kioskMode && value.is_custom) {
                return;
            }
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
        return Boolean(selection.getMissingAttributeValue(product.attribute_line_ids));
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
        } else if (this.isAttributeSelection()) {
            if (!this.isNextEnabled()) {
                // Disable product selection if not all attributes are selected
                const choiceState = this.currentChoiceState;
                delete choiceState.selectedItems[choiceState.displayAttributesOfItem.id];
            }
            this.currentChoiceState.displayAttributesOfItem = false;
        } else {
            this.state.selectedChoiceIndex = Math.max(0, this.state.selectedChoiceIndex - 1);
        }
        this.resetScrollPosition();
    }

    isNextEnabled() {
        if (this.currentChoiceState.displayAttributesOfItem) {
            const selectedItem = this.currentChoiceState.displayAttributesOfItem;
            if (!this.hasMissingAttributeValues(selectedItem) && !this.isArchivedCombination()) {
                return true;
            }
        } else {
            if (
                this.getSelectedItemCount() >= this.selectedChoice.qty_free ||
                this.selectedChoice.qty_free === 0
            ) {
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

        let newSectionDisplayed = false;
        const choices = this.comboChoices;
        const isLastChoice = this.state.selectedChoiceIndex === choices.length - 1;
        const isAttributeSelection = this.isAttributeSelection();
        const hasMultiItemSelection = this.hasMultiItemSelection;
        if (isAttributeSelection && hasMultiItemSelection) {
            // If we're in attribute selection for a multi-item choice, reset to item selection
            this.currentChoiceState.displayAttributesOfItem = false;
            newSectionDisplayed = true;
        } else if (!isAttributeSelection && !hasMultiItemSelection) {
            const selectedItem = this.getSelectedItems()[0];
            if (selectedItem) {
                // Display attributes of the selected item, if any are available
                const hasAttributes = selectedItem.item.product_id.attribute_line_ids.length > 0;
                if (hasAttributes) {
                    this.currentChoiceState.displayAttributesOfItem = selectedItem.item;
                    newSectionDisplayed = true;
                }
            }
        }

        if (!newSectionDisplayed) {
            if (isLastChoice) {
                this.state.showResume = true;
            } else {
                this.state.selectedChoiceIndex += 1;
            }
            newSectionDisplayed = true;
        }

        if (newSectionDisplayed) {
            this.resetScrollPosition();
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

            const selectedItems = this.getSelectedItems(choice);
            if (selectedItems.length === 0) {
                return;
            }
            const missingAttributes = selectedItems.some((s) =>
                this.hasMissingAttributeValues(s.item)
            );
            if (missingAttributes) {
                return;
            }
        }

        this.state.showResume = false;
        this.state.selectedChoiceIndex = choiceIndex;
        this.currentChoiceState.displayAttributesOfItem = false;
        this.resetScrollPosition();
    }

    resetScrollPosition() {
        // Ensure the section below the large image is visible to minimize excessive scrolling for the user
        setTimeout(() => {
            const el = window.document.getElementById("k-combo-scroll-target");
            if (el) {
                this.scrollContainerRef.el?.scrollTo({ top: el.offsetTop - 20 });
            }
        }, 1);
    }

    getSelection() {
        return this.comboChoices.map((choice, index) => {
            const choiceState = this.state.choices[index];
            const selectedItems = choiceState ? this.getSelectedItems(choiceState) : [];
            const comboItems = selectedItems.map((selectedItem) => {
                const comboItem = selectedItem.item;
                const product = comboItem.product_id;
                const selectedAttributes = [];
                const selectedValues = this.state.selectedValues[product.id];

                for (const line of product.attribute_line_ids) {
                    const selected = selectedValues?.getSelectedAttributeValues(line) ?? [];
                    if (selected.length > 0) {
                        selectedAttributes.push({
                            attribute_line_id: line,
                            attribute_ids: selected,
                            names: selected
                                .map((attrValue) => {
                                    const customValue = attrValue.is_custom
                                        ? selectedValues.getCustomValue(
                                              attrValue.attribute_id,
                                              attrValue
                                          )?.custom_value
                                        : null;
                                    return customValue
                                        ? `${attrValue.name}: ${customValue}`
                                        : attrValue.name;
                                })
                                .join(", "),
                        });
                    }
                }
                return {
                    combo_item_id: comboItem,
                    qty: selectedItem.qty,
                    product_id: product,
                    attributes: selectedAttributes,
                    custom_attributes: selectedValues?.getAllCustomValues(),
                };
            });

            return {
                combo_choice_id: choice,
                combo_items: comboItems,
            };
        });
    }

    getComboSelection() {
        return this.getSelection().flatMap((choice) =>
            choice.combo_items.map((item) => ({
                combo_item_id: item.combo_item_id,
                qty: item.qty,
                configuration: {
                    attribute_custom_values: item.custom_attributes,
                    attribute_value_ids:
                        item.attributes?.flatMap((attr) =>
                            attr.attribute_ids.map((attrVal) => attrVal.id)
                        ) || [],
                    price_extra: 0,
                },
            }))
        );
    }

    addToCart() {
        this.selfOrder.addToCart(
            this.props.productTemplate,
            this.state.qty,
            "",
            {},
            {},
            this.getComboSelection()
        );

        this.goBack();
    }

    getComboPrice() {
        return computeTotalComboPrice(
            this.selfOrder,
            this.props.productTemplate,
            this.getComboSelection(),
            this.state.qty
        );
    }

    goBack() {
        this.router.navigate("product_list");
    }

    scrollUpToRequired() {
        const selectedItem = this.currentChoiceState.displayAttributesOfItem.product_id;
        const selection = this.state.selectedValues[selectedItem.id];
        const missingAttribute = selection?.getMissingAttributeValue(
            selectedItem.attribute_line_ids
        );
        document
            .getElementById(missingAttribute?.attribute_id?.id)
            ?.scrollIntoView({ behavior: "smooth" });
    }

    /*
     // TODO
     get editableProductLine() {
        const order = this.selfOrder.currentOrder;
        return !(
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }*/
}
