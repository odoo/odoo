import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useState } from "@odoo/owl";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

/**
 * @props partner
 */
patch(ActionpadWidget, {
    props: {
        ...ActionpadWidget.props,
        setTable: { type: Function, optional: true },
        assignOrder: { type: Function, optional: true },
    },
});

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
    get hasChangesToPrint() {
        let hasChange = this.pos.getOrderChanges();
        hasChange =
            hasChange.generalCustomerNote == ""
                ? true // for the case when removed all general note
                : hasChange.count || hasChange.generalCustomerNote || hasChange.modeUpdate;
        return hasChange;
    },
<<<<<<< saas-18.1:addons/pos_restaurant/static/src/app/screens/product_screen/actionpad_widget/actionpad_widget.js
    async submitOrder() {
        await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
        this.pos.showDefault();
||||||| c8ebc003f4a68875c3d73b17494898cac9f124e7:addons/pos_restaurant/static/src/overrides/components/product_screen/actionpad_widget/actionpad_widget.js
    get swapButtonClasses() {
        return {
            "highlight btn-primary justify-content-between": this.displayCategoryCount.length,
            "btn-light pe-none disabled justify-content-center": !this.displayCategoryCount.length,
            altlight: !this.hasChangesToPrint && this.currentOrder?.hasSkippedChanges(),
        };
    },
    submitOrder() {
        this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
=======
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
>>>>>>> ddf200a3d53effdaa45457e4f225855a36430fa7:addons/pos_restaurant/static/src/overrides/components/product_screen/actionpad_widget/actionpad_widget.js
    },
    hasQuantity(order) {
        if (!order) {
            return false;
        } else {
            return order.lines.reduce((totalQty, line) => totalQty + line.getQuantity(), 0) > 0;
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
