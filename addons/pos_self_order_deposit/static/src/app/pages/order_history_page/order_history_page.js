import { patch } from "@web/core/utils/patch";
import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";

patch(OrdersHistoryPage.prototype, {
    getLines(order) {
        return order.getOrderlines().filter((line) => !line.deposit_main_line_id);
    },
    getPrice(line) {
        return super.getPrice(line) + (line.depositLine?.displayPrice || 0);
    },
    getDepositPrice(line) {
        return this.selfOrder.formatMonetary(line.depositLine.displayPrice);
    },
    getDepositTotal(order) {
        return order.lines
            .filter((line) => line.deposit_main_line_id)
            .reduce((total, line) => total + line.displayPrice, 0);
    },
});
