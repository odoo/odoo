import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { patch } from "@web/core/utils/patch";

patch(OrderTabs.prototype, {
    newFloatingOrder() {
        const order = super.newFloatingOrder(...arguments);

        if (this.pos.config.module_pos_restaurant) {
            order.setBooked(true);
        }
    },
});
