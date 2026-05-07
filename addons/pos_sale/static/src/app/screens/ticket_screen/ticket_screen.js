import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        const refundOrder = this.pos.selectedOrder;
        if (!refundOrder?.is_refund) {
            return;
        }
        for (const line of refundOrder.lines) {
            const originalLine = line.refunded_orderline_id;
            if (!originalLine) {
                continue;
            }
            if (originalLine.sale_order_origin_id) {
                line.sale_order_origin_id = originalLine.sale_order_origin_id;
            }
            if (originalLine.sale_order_line_id) {
                line.sale_order_line_id = originalLine.sale_order_line_id;
            }
        }
    },
});
