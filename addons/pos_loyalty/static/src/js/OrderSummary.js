/** @odoo-module **/

import { OrderSummary } from "@point_of_sale/js/Screens/ProductScreen/OrderSummary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, "pos_loyalty.OrderSummary", {
    getLoyaltyPoints() {
        const order = this.env.pos.get_order();
        return order.getLoyaltyPoints();
    },
});
