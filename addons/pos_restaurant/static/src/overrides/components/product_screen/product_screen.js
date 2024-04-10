/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, useState } from "@odoo/owl";

patch(ProductScreen.prototype, {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);

        this.uiState = useState({
            clicked: false,
        });

        onMounted(() => {
            this.pos.addPendingOrder([this.pos.get_order().id]);
        });
    },
    get selectedOrderlineQuantity() {
        const order = this.pos.get_order();
        const orderline = order.get_selected_orderline();
        if (this.pos.config.module_pos_restaurant && this.pos.orderPreparationCategories.size) {
            let orderline_name = orderline.product_id.display_name;
            if (orderline.description) {
                orderline_name += " (" + orderline.description + ")";
            }
            const changes = Object.values(this.pos.getOrderChanges().orderlines).find(
                (change) => change.name == orderline_name
            );
            return changes ? changes.quantity : false;
        }
        return super.selectedOrderlineQuantity;
    },
    get selectedOrderlineTotal() {
        return this.env.utils.formatCurrency(
            this.pos.get_order().get_selected_orderline().get_display_price()
        );
    },
    get nbrOfChanges() {
        return this.pos.getOrderChanges().nbrOfChanges;
    },
    get swapButton() {
        return this.pos.config.module_pos_restaurant && this.pos.orderPreparationCategories.size;
    },
    get displayCategoryCount() {
        return this.pos.categoryCount.slice(0, 3);
    },
    async submitOrder() {
        if (!this.uiState.clicked) {
            this.uiState.clicked = true;
            try {
                await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
            } finally {
                this.uiState.clicked = false;
            }
        }
    },
    get primaryReviewButton() {
        return (
            !this.primaryOrderButton &&
            !this.pos.get_order().is_empty() &&
            this.pos.config.module_pos_restaurant
        );
    },
    get primaryOrderButton() {
        return (
            this.pos.getOrderChanges().nbrOfChanges !== 0 && this.pos.config.module_pos_restaurant
        );
    },
});
