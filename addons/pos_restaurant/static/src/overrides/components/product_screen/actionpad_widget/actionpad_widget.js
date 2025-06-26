import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useState } from "@odoo/owl";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
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
        return (
            this.pos.config.module_pos_restaurant && this.pos.mainScreen.component !== TicketScreen
        );
    },
    get currentOrder() {
        return this.pos.get_order();
    },
    get hasChangesToPrint() {
        let hasChange = this.pos.getOrderChanges();
        hasChange =
            hasChange.generalNote == ""
                ? true // for the case when removed all general note
                : hasChange.count || hasChange.generalNote || hasChange.modeUpdate;
        return hasChange;
    },
    get swapButtonClasses() {
        return {
            "highlight btn-primary justify-content-between": this.displayCategoryCount.length,
            "btn-light pe-none disabled justify-content-center": !this.displayCategoryCount.length,
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
        return (
            this.currentOrder?.lines?.length &&
            !this.hasChangesToPrint &&
            this.hasQuantity(this.currentOrder)
        );
    },
    get displayCategoryCount() {
        return this.pos.categoryCount.slice(0, 4);
    },
    get isCategoryCountOverflow() {
        if (this.pos.categoryCount.length > 4) {
            return true;
        }
        return false;
    },
});
