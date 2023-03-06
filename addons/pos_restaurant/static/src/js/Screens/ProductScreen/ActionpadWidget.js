/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/js/Screens/ProductScreen/ActionpadWidget";
import { nbsp } from "@web/core/utils/strings";
/**
 * @props partner
 */

patch(ActionpadWidget.prototype, "point_of_sale.ActionpadWidget", {
    get swapButton() {
        return (
            this.props.actionName === "Payment" &&
            this.pos.globalState.config.module_pos_restaurant &&
            this.pos.globalState.orderPreparationCategories.size
        );
    },
    get currentOrder() {
        return this.pos.globalState.get_order();
    },
    get addedClasses() {
        if (!this.currentOrder) {
            return {};
        }
        const hasChanges = this.currentOrder.hasChangesToPrint();
        const skipped = hasChanges ? false : this.currentOrder.hasSkippedChanges();
        return {
            highlight: hasChanges,
            altlight: skipped,
        };
    },
    async submitOrder() {
        if (!this.clicked) {
            this.clicked = true;
            try {
                await this.pos.sendOrderInPreparation(this.currentOrder);
            } finally {
                this.clicked = false;
            }
        }
    },
    hasQuantity(order) {
        if (!order) {
            return false;
        } else {
            return (
                order.orderlines.reduce((totalQty, line) => totalQty + line.get_quantity(), 0) > 0
            );
        }
    },
    get highlightPay() {
        return (
            this._super(...arguments) &&
            this.pos.globalState.orderPreparationCategories.size &&
            !this.currentOrder.hasChangesToPrint() &&
            this.hasQuantity(this.currentOrder)
        );
    },
    get categoryCount() {
        const categories = {};
        const orderChange = this.currentOrder.getOrderChanges();
        for (const idx in orderChange) {
            const orderline = orderChange[idx];
            const category = this.pos.globalState.db.get_product_by_id(orderline.product_id)
                .pos_categ_id[1];
            const numProd = orderline.quantity;
            categories[category] = categories[category] ? categories[category] + numProd : numProd;
        }
        let result = "";
        for (const key in categories) {
            result = result + categories[key] + nbsp + key + " | ";
        }
        return result.slice(0, -2);
    },
});
