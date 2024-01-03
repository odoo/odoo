/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
/**
 * @props partner
 */

patch(ActionpadWidget.prototype, {
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
            "highlight btn-primary": this.hasChangesToPrint,
            altlight: !this.hasChangesToPrint && this.currentOrder?.hasSkippedChanges(),
        };
    },
    async submitOrder() {
        if (!this.clicked) {
            this.clicked = true;
            try {
                await this.pos.sendOrderInPreparationUpdateLastChange(this.currentOrder);
            } finally {
                this.clicked = false;
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
    get categoryCount() {
        const orderChange = this.pos.getOrderChanges().orderlines;

        const categories = Object.values(orderChange).reduce((acc, curr) => {
            const categories =
                this.pos.models["product.product"].get(curr.product_id)?.pos_categ_ids || [];

            for (const category of categories) {
                if (category) {
                    if (!acc[category.id]) {
                        acc[category.id] = {
                            count: curr.quantity,
                            name: category.name,
                        };
                    } else {
                        acc[category.id].count += curr.quantity;
                    }
                }
            }

            return acc;
        }, {});
        return Object.values(categories);
    },
    get displayCategoryCount() {
        return this.categoryCount.slice(0, 3);
    },
    get isCategoryCountOverflow() {
        if (this.categoryCount.length > 3) {
            return true;
        }
        return false;
    },
});
