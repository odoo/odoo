/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/models/order";

patch(Order.prototype, {
    setup(order) {
        super.setup(...arguments);
        this.take_away = order.take_away;
        this.table_stand_number = order.table_stand_number;
    },
});
