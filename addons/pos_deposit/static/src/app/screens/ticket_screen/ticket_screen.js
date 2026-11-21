import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    onClickOrderline(orderline) {
        return super.onClickOrderline(orderline.deposit_main_line_id || orderline);
    },
    _onUpdateSelectedOrderline(event) {
        const order = this.getSelectedOrder();
        const selectedLine = order?.lines.find((line) => line.id == this.getSelectedOrderlineId());
        const result = super._onUpdateSelectedOrderline(event);
        for (const line of selectedLine?.getAllLinesInCombo() || []) {
            const depositLine = line.depositLine;
            if (depositLine && line.qty) {
                const depositRefundDetail = this.getToRefundDetail(depositLine);
                depositRefundDetail.qty = Math.min(
                    (depositLine.qty / line.qty) * this.getToRefundDetail(line).qty,
                    depositRefundDetail.refundableQty
                );
            }
        }
        return result;
    },
    postRefund(destinationOrder) {
        super.postRefund(...arguments);
        for (const line of destinationOrder.lines) {
            const mainLine = line.refunded_orderline_id?.deposit_main_line_id;
            const refundMainLine = mainLine?.refund_orderline_ids.find(
                (refundLine) => refundLine.order_id === destinationOrder
            );
            if (refundMainLine) {
                line.deposit_main_line_id = refundMainLine;
            }
        }
    },
});
