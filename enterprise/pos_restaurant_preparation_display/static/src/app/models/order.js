import { patch } from "@web/core/utils/patch";
import { Order } from "@pos_preparation_display/app/models/order";

patch(Order.prototype, {
    setup(order) {
        super.setup(...arguments);
        this.table = order.table;
        this.floating_order_name = order.floating_order_name;
    },
});
