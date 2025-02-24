import { Component, onWillUnmount, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ComboSelection } from "@pos_self_order/app/components/combo_selection/combo_selection";
import { useService } from "@web/core/utils/hooks";

export class ComboPage extends Component {
    static template = "pos_self_order.ComboPage";
    static props = ["product"];
    static components = { ComboSelection };

    setup() {
        this.selfOrder = useSelfOrder();
        this.selfOrder.lastEditedProductId = this.props.product.id;
        this.router = useService("router");
        useSubEnv({
            selectedValues: {},
            customValues: {},
            editable: this.editableProductLine,
            currentComboItemId: {
                value: null,
            },
        });

        if (!this.props.product) {
            this.router.navigate("product_list");
            return;
        }

        this.state = useState({
            currentComboIndex: 0,
            selectedCombos: [],
            showResume: false,
            selectedProduct: null,
            showQtyButtons: false,
            editMode: false,
            qty: 1,
            selectedValues: this.env.selectedValues,
        });

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });
    }

    get editableProductLine() {
        const order = this.selfOrder.currentOrder;
        return !(
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }

    get currentCombo() {
        return this.comboIds[this.state.currentComboIndex];
    }

    getSelectedValues(attrValIds) {
        return this.selfOrder.models["product.template.attribute.value"].filter((c) =>
            attrValIds.includes(c.id)
        );
    }

    isEveryValueSelected() {
        return Object.values(this.state.selectedValues).every((value) => value);
    }

    isArchivedCombination() {
        const variantAttributeValueIds = Object.values(this.state.selectedValues)
            .filter((attr) => typeof attr !== "object")
            .map((attr) => Number(attr));
        return this.props.product._isArchivedCombination(variantAttributeValueIds);
    }

    resetState() {
        this.state.selectedProduct = null;
        this.state.showQtyButtons = false;

        // Cannot assign to read only property
        for (const key in this.env.selectedValues) {
            delete this.env.selectedValues[key];
        }

        for (const key in this.env.customValues) {
            delete this.env.customValues[key];
        }
    }

    next() {
        const combo = this.currentCombo;
        const index = this.state.selectedCombos.findIndex((c) => c.id === combo.id);
        const comboItem = this.selfOrder.models["product.combo.item"].get(
            this.env.currentComboItemId.value
        );
        const selectedCombo = {
            combo_item_id: comboItem,
            configuration: {
                attribute_custom_values: Object.values(this.env.customValues),
                attribute_value_ids: Object.values(this.env.selectedValues).map((s) => parseInt(s)),
                price_extra: 0,
            },
        };
        if (index !== -1) {
            this.state.selectedCombos[index] = selectedCombo;
        } else {
            this.state.selectedCombos.push(selectedCombo);
        }
        this.resetState();
        if (this.state.editMode) {
            this.state.editMode = false;
            this.state.showResume = true;
            this.state.showQtyButtons = true;
            return;
        }
        this.state.currentComboIndex++;
        if (this.state.currentComboIndex == this.comboIds.length) {
            this.state.showResume = true;
        }
    }

    back() {
        this.router.navigate("product_list");
    }

    changeQuantity(increase) {
        if (!increase && this.state.qty === 1) {
            return;
        }

        return increase ? this.state.qty++ : this.state.qty--;
    }

    async addToCart() {
        if (this.selfOrder.editedLine) {
            this.selfOrder.editedLine.delete();
        }

        this.selfOrder.addToCart(
            this.props.product,
            this.state.qty,
            "",
            {},
            {},
            this.state.selectedCombos
        );
        this.router.back();
    }

    editCombo(combo_id) {
        this.state.currentComboIndex = this.comboIds.findIndex((c) => c === combo_id);
        this.state.showResume = false;
        this.state.editMode = true;
        this.state.showQtyButtons = false;
    }

    get showQtyButtons() {
        return this.state.showQtyButtons && this.props.product.self_order_available;
    }

    get comboIds() {
        const combo = this.props.product.combo_ids;
        return combo.filter(
            (c) =>
                c.combo_item_ids.length > 1 ||
                (c.combo_item_ids.some((c) => c.product_id.attribute_line_ids.length !== 0) &&
                    !c.combo_item_ids.every((c) => c.product_id.isCombo()))
        );
    }
}
