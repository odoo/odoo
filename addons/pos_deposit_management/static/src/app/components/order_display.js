import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        if (!this.order.config_id?.module_pos_deposit_management) {
            return super.comboSortedLines;
        }
        return this.order.getOrderlines();
    },
});
