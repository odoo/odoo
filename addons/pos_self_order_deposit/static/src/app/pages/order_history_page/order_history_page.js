import { patch } from "@web/core/utils/patch";
import { OrdersHistoryPage } from "@pos_self_order/app/pages/order_history_page/order_history_page";

patch(OrdersHistoryPage.prototype, {
    getLines(order) {
        return order.getOrderlines().filter((line) => !line.deposit_main_line_id);
    },
    getPrice(line) {
        const lines = [line, ...line.combo_line_ids];
        return (
            super.getPrice(line) +
            lines.reduce((sum, l) => sum + (l.depositLine?.displayPrice || 0), 0)
        );
    },
    getDepositPrice(line) {
        return this.selfOrder.formatMonetary(line.depositLine.displayPrice);
    },
});
