/** @odoo-module **/

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, "pos_loyalty.OrderSummary", {
    getLoyaltyPoints() {
        const order = this.pos.get_order();
        return order.getLoyaltyPoints();
    },
});
