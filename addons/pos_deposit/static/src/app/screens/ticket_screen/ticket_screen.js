import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    onClickOrderline(orderline) {
        return super.onClickOrderline(orderline.deposit_main_line_id || orderline);
    },
    _onUpdateSelectedOrderline(event) {
        const order = this.getSelectedOrder();
        const selected = order?.lines.find((l) => l.id == this.getSelectedOrderlineId());
        if (selected?.deposit_main_line_id) {
            this.state.selectedOrderlineIds[order.id] = selected.deposit_main_line_id.id;
        }
        const result = super._onUpdateSelectedOrderline(event);
        const root = selected?.deposit_main_line_id || selected;
        for (const line of [root?.combo_parent_id || root].flatMap(
            (l) => l && [l, ...l.combo_line_ids]
        )) {
            const deposit = line?.depositLine;
            if (deposit && line.qty) {
                const detail = this.getToRefundDetail(deposit);
                detail.qty = Math.min(
                    (deposit.qty / line.qty) * this.getToRefundDetail(line).qty,
                    detail.refundableQty
                );
            }
        }
        return result;
    },
    postRefund(destinationOrder) {
        super.postRefund(...arguments);
        for (const line of destinationOrder.lines) {
            const main = line.refunded_orderline_id?.deposit_main_line_id;
            const refundMain = main?.refund_orderline_ids.find(
                (l) => l.order_id === destinationOrder
            );
            if (refundMain) {
                line.deposit_main_line_id = refundMain;
            }
        }
    },
});
