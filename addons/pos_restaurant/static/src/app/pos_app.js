import { Chrome } from "@point_of_sale/app/pos_app";
import { patch } from "@web/core/utils/patch";

patch(Chrome.prototype, {
    sendOrderToCustomerDisplay(selectedOrder, scaleData) {
        super.sendOrderToCustomerDisplay(selectedOrder, scaleData);
        if (this.pos.config.module_pos_restaurant) {
            this.pos.addPendingOrder([selectedOrder.id]);
        }
    },
});
