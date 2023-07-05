/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_self_order/mobile/models/order";

patch(Order.prototype, "pos_restaurant_self_order.Order", {
    setup(order) {
        this._super(...arguments);
        this.table_id = order.table_id || null;
    },
});
