import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
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
    async submitOrder() {
        await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
        this.pos.showDefault();
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
