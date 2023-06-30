/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, "pos_restaurant.ProductScreen", {
    /**
     * @override
     */
    get selectedOrderlineQuantity() {
        const order = this.pos.get_order();
        const orderline = order.get_selected_orderline();
        if (
            this.pos.config.module_pos_restaurant &&
            this.pos.orderPreparationCategories.size
        ) {
            let orderline_name = orderline.product.display_name;
            if (orderline.description) {
                orderline_name += " (" + orderline.description + ")";
            }
            const changes = Object.values(order.getOrderChanges().orderlines).find(
                (change) => change.name == orderline_name
            );
            return changes ? changes.quantity : false;
        }
        return this._super(...arguments);
    },
    get selectedOrderlineTotal() {
        return this.env.utils.formatCurrency(
            this.pos.get_order().get_selected_orderline().get_display_price()
        );
    },
    get swapButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.orderPreparationCategories.size
        );
    },
    submitOrder() {
        this.pos.sendOrderInPreparation(this.pos.get_order());
    },
    primaryPayButton() {
        return (
            !this.currentOrder.is_empty() &&
            ((!this.swapButton && this._super(...arguments)) ||
                (this.swapButton && this.pos.get_order().getOrderChanges().count > 0))
        );
    },
});
