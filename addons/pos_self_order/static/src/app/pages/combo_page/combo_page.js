/** @odoo-module */

import { Component, onWillUnmount, useState, useSubEnv } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/self_order_service";
import { ComboSelection } from "@pos_self_order/app/components/combo_selection/combo_selection";
import { useService } from "@web/core/utils/hooks";
import { Line } from "@pos_self_order/app/models/line";
import { attributeFlatter, attributeFormatter } from "@pos_self_order/app/utils";
import { constructFullProductName } from "@point_of_sale/utils";

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
            currentComboLineId: {
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
        });

        this.addPreselectedChoices();

        onWillUnmount(() => {
            this.selfOrder.editedLine = null;
        });
    }

    addPreselectedChoices() {
        for (const comboId of this.props.product.pos_combo_ids.filter(
            (posComboId) => !this.comboIds.includes(posComboId)
        )) {
            const combo = this.selfOrder.comboByIds[comboId];
            const product = this.selfOrder.productByIds[combo.combo_line_ids[0].product_id[0]];
            const selectedCombo = {
                id: combo.id,
                name: combo.name,
                combo_line_id: this.env.currentComboLineId.value,
                product: {
                    id: product.id,
                    name: product.name,
                    variants: {},
                    customValues: {},
                },
            };
            this.state.selectedCombos.push(selectedCombo);
        }
    }

    get editableProductLine() {
        const order = this.selfOrder.currentOrder;
        return !(
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }

    get currentComboId() {
        return this.comboIds[this.state.currentComboIndex];
    }

    get currentCombo() {
        return this.selfOrder.comboByIds[this.currentComboId];
    }

    getAttributeSelected(combo) {
        const flatAttribute = attributeFlatter(combo.variants);
        const customAttribute = combo.customValues;
        return attributeFormatter(this.selfOrder.attributeById, flatAttribute, customAttribute);
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
        const selectedCombo = {
            id: combo.id,
            name: combo.name,
            combo_line_id: this.env.currentComboLineId.value,
            product: {
                id: this.state.selectedProduct.id,
                name: this.state.selectedProduct.name,
                variants: { ...this.env.selectedValues },
                customValues: { ...this.env.customValues },
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
            this.selfOrder.currentOrder.removeLine(this.selfOrder.editedLine.uuid);
        }

        const lines = this.selfOrder.currentOrder.lines;
        const parent_line = new Line({
            id: null,
            uuid: null,
            qty: this.state.qty,
            price_unit: this.props.product.price_info.price_without_tax,
            product_id: this.props.product.id,
            full_product_name: this.props.product.name,
            attribute_value_ids: [],
            custom_attribute_value_ids: [],
            combo_parent_uuid: null,
            combo_id: null,
        });
        lines.push(parent_line);
        for (const combo of this.state.selectedCombos) {
            const child_line = new Line({
                id: null,
                uuid: null,
                qty: this.state.qty,
                product_id: combo.product.id,
                attribute_value_ids: attributeFlatter(combo.product.variants),
                custom_attribute_value_ids: Object.values(combo.product.customValues),
                combo_parent_uuid: parent_line.uuid,
                combo_id: combo.id,
                combo_line_id: combo.combo_line_id,
            });
            child_line.full_product_name = constructFullProductName(child_line);
            lines.push(child_line);
            parent_line.child_lines.push(child_line);
        }

        await this.selfOrder.getPricesFromServer();
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
        return this.props.product.pos_combo_ids.filter(
            (comboId) =>
                this.selfOrder.comboByIds[comboId].combo_line_ids.length > 1 ||
                (this.selfOrder.productByIds[
                    this.selfOrder.comboByIds[comboId].combo_line_ids[0].product_id[0]
                ].attributes.length != 0 &&
                    !this.selfOrder.productByIds[
                        this.selfOrder.comboByIds[comboId].combo_line_ids[0].product_id[0]
                    ].isCombo)
        );
    }
}
