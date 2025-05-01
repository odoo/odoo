import {
    Component,
    onWillUnmount,
    useState,
    useSubEnv,
    useRef,
    onMounted,
    onPatched,
} from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { KioskAttributeSelection } from "@pos_self_order/app/components/kiosk_attribute_selection/attribute_selection";
import { KioskQuantityWidget } from "@pos_self_order/app/components/kiosk_quantity/quantity_widget";
import { computeTotalComboPrice } from "../../services/card_utils";

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
            comboPrice: 0,
            topShadowOpacity: 0,
            bottomShadowOpacity: 1,
        });
        this.onAttributeSelection = this.onAttributeSelection.bind(this);
        this.scrollContainerRef = useRef("scrollContainer");
        this.updateShadows = this.updateShadows.bind(this);

        onMounted(() => {
            const el = this.scrollContainerRef?.el;
            if (el) {
                el.addEventListener("scroll", this.updateShadows);
                window.addEventListener("resize", this.updateShadows);
                this.updateShadows();
            }

            requestAnimationFrame(this.updateShadows);
        });

        onPatched(() => {
            this.updateShadows();
        });

        onWillUnmount(() => {
            const el = this.scrollContainerRef?.el;
            if (el) {
                el.removeEventListener("scroll", this.updateShadows);
            }
            window.removeEventListener("resize", this.updateShadows);
        });
    }

    updateShadows() {
        if (!this.scrollContainerRef.el) {
            return;
        }

        const container = this.scrollContainerRef.el;
        const { scrollTop, scrollHeight, clientHeight } = container;

        const threshold = 2;
        this.state.topShadowOpacity = scrollTop > threshold ? 1 : 0;
        this.state.bottomShadowOpacity =
            scrollTop + clientHeight < scrollHeight - threshold ? 1 : 0;
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
        return this.getSelectedItemCount() < this.selectedChoice.qty_max;
    }

    getSelectedItemCount() {
        return this.getSelectedItems().reduce((sum, item) => sum + item.qty, 0);
    }

    get hasSelectedItems() {
        return this.getSelectedItems().some((item) => item.qty > 0);
    }

    changeItemQuantity(item, value, evt) {
        evt.stopPropagation();

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

        const choices = this.comboChoices;
        const isLastChoice = this.state.selectedChoiceIndex === choices.length - 1;
        if (this.isAttributeSelection() || this.hasMultiItemSelection) {
            if (this.isAttributeSelection() && this.hasMultiItemSelection) {
                /// If we're in attribute selection for a multi-item choice, reset to item selection
                this.currentChoiceState.displayAttributesOfItem = false;
                return;
            }
        } else {
            const selectedItem = this.getSelectedItems()[0];
            if (selectedItem) {
                const hasAttributes = selectedItem.item.product_id.attribute_line_ids.length > 0;
                if (hasAttributes) {
                    this.currentChoiceState.displayAttributesOfItem = selectedItem.item;
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
            const selectedItems = choiceState ? this.getSelectedItems(choiceState) : [];
            const comboItems = selectedItems.map((selectedItem) => {
                const comboItem = selectedItem.item;
                const product = comboItem.product_id;
                const selectedAttributes = [];
                const selectedValues = this.state.selectedValues[product.id] ?? {};
                for (const line of product.attribute_line_ids) {
                    const selected = selectedValues.getSelectedAttributeValues?.(line) ?? [];
                    if (selected.length > 0) {
                        selectedAttributes.push({
                            attribute_line_id: line,
                            attribute_ids: selected,
                            names: selected.map((attr) => attr.name).join(", "),
                        });
                    }
                }
                return {
                    combo_item_id: comboItem,
                    qty: selectedItem.qty,
                    product_id: product,
                    attributes: selectedAttributes,
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
                    attribute_custom_values: [],
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

        this.router.back();
    }

    getComboPrice() {
        return computeTotalComboPrice(
            this.selfOrder,
            this.props.productTemplate,
            this.getComboSelection(),
            this.state.qty
        );
    }
}
