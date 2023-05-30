/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { nbsp } from "@web/core/utils/strings";
/**
 * @props partner
 */

patch(ActionpadWidget.prototype, "point_of_sale.ActionpadWidget", {
    get swapButton() {
        return this.props.actionType === "payment" && this.pos.config.module_pos_restaurant;
    },
    get currentOrder() {
        return this.pos.get_order();
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
            !this.currentOrder.hasChangesToPrint() &&
            this.hasQuantity(this.currentOrder)
        );
    },
    get categoryCount() {
        const categories = {};
        const orderChange = this.currentOrder.getOrderChanges().orderlines;
        for (const idx in orderChange) {
            const orderline = orderChange[idx];
            const categoryId = this.pos.db.get_product_by_id(orderline.product_id).pos_categ_ids[0];
            const category = this.pos.db.category_by_id[categoryId].name;
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
