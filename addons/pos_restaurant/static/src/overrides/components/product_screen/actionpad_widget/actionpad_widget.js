/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useState } from "@odoo/owl";
/**
 * @props partner
 */

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.uiState = useState({
            clicked: false,
        });
    },
    get swapButton() {
        return this.props.actionType === "payment" && this.pos.config.module_pos_restaurant;
    },
    get currentOrder() {
        return this.pos.get_order();
    },
    get hasChangesToPrint() {
        const hasChange = this.pos.getOrderChanges();
        return hasChange.count;
    },
    get swapButtonClasses() {
        return {
            "highlight btn-primary": this.displayCategoryCount.length,
            "pe-none": !this.displayCategoryCount.length,
            altlight: !this.hasChangesToPrint && this.currentOrder?.hasSkippedChanges(),
        };
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
    hasQuantity(order) {
        if (!order) {
            return false;
        } else {
            return order.lines.reduce((totalQty, line) => totalQty + line.get_quantity(), 0) > 0;
        }
    },
    get highlightPay() {
        return super.highlightPay && !this.hasChangesToPrint && this.hasQuantity(this.currentOrder);
    },
    get displayCategoryCount() {
        return this.pos.categoryCount.slice(0, 3);
    },
    get isCategoryCountOverflow() {
        if (this.pos.categoryCount.length > 3) {
            return true;
        }
        return false;
    },
});
