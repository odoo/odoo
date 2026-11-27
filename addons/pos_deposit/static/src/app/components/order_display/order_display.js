import { sortDepositLines } from "@pos_deposit/app/utils/sort_deposit_lines";
import { patch } from "@web/core/utils/patch";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

patch(OrderDisplay.prototype, {
    get comboSortedLines() {
        if (!this.order.config.module_pos_deposit) {
            return super.comboSortedLines;
        }
        return sortDepositLines(super.comboSortedLines);
    },
});
