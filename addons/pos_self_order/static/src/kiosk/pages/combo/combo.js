/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";
import { ComboSelection } from "@pos_self_order/kiosk/components/combo_selection/combo_selection";
import { useService } from "@web/core/utils/hooks";
import { Line } from "@pos_self_order/common/models/line";

export class Combo extends Component {
    static template = "pos_self_order.Combo";
    static props = ["product"];
    static components = { KioskTemplate, ComboSelection };

    setup() {
        this.selfOrder = useselfOrder();
        this.selfOrder.lastEditedProductId = this.props.product.id;
        this.router = useService("router");

        if (!this.props.product) {
            this.router.navigate("productList");
            return;
        }

        this.state = useState({
            currentComboIndex: 0,
            selectedCombos: [],
            showResume: false,
            selectedProduct: null,
            selectedVariants: {},
            qty: 1,
            showQtyButtons: false,
            editMode: false,
        });
    }

    get currentComboId() {
        return this.props.product.pos_combo_ids[this.state.currentComboIndex];
    }

    get currentCombo() {
        return this.selfOrder.comboByIds[this.currentComboId];
    }

    resetState() {
        this.state.selectedProduct = null;
        this.state.selectedVariants = {};
        this.state.showQtyButtons = false;
    }

    next() {
        const combo = this.currentCombo;
        const index = this.state.selectedCombos.findIndex((c) => c.id === combo.id);
        if (index !== -1) {
            this.state.selectedCombos[index] = {
                id: combo.id,
                name: combo.name,
                product: {
                    id: this.state.selectedProduct.id,
                    name: this.state.selectedProduct.name,
                    variants: Object.entries(this.state.selectedVariants),
                },
            };
        } else {
            this.state.selectedCombos.push({
                id: combo.id,
                name: combo.name,
                product: {
                    id: this.state.selectedProduct.id,
                    name: this.state.selectedProduct.name,
                    variants: Object.entries(this.state.selectedVariants),
                },
            });
        }
        this.resetState();
        if (this.state.editMode) {
            this.state.editMode = false;
            this.state.showResume = true;
            this.state.showQtyButtons = true;
            return;
        }
        this.state.currentComboIndex++;
        if (this.state.currentComboIndex == this.props.product.pos_combo_ids.length) {
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
        const lines = this.selfOrder.currentOrder.lines;
        const parent_line = new Line({
            id: null,
            uuid: null,
            qty: this.state.qty,
            price_unit: this.props.product.price_info.price_without_tax,
            product_id: this.props.product.id,
            full_product_name: this.props.product.name,
            selected_attributes: {},
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
                full_product_name: combo.product.name,
                selected_attributes: Object.fromEntries(combo.product.variants),
                combo_parent_uuid: parent_line.uuid,
                combo_id: combo.id,
            });
            lines.push(child_line);
            parent_line.child_lines.push(child_line);
        }

        await this.selfOrder.getPricesFromServer();

        this.router.back();
    }

    editCombo(combo_id) {
        this.state.currentComboIndex = this.state.selectedCombos.findIndex(
            (c) => c.id === combo_id
        );
        this.state.showResume = false;
        this.state.editMode = true;
        this.state.showQtyButtons = false;
    }
}
