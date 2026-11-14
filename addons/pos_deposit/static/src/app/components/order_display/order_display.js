import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        return this.order.sortDepositLines(super.comboSortedLines);
    },
});
