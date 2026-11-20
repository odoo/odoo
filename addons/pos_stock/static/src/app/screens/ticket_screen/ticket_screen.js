import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    getOrderSortPriority(order) {
        // Paid orders due for pickup come first, so the cashier finds them when the
        // customer shows up.
        if (this.isOrderDoneOrPaid(order) && order.isPickupDue) {
            return 1;
        }
        return super.getOrderSortPriority(order);
    },
    getRefundLinesDetails(refundDetail, destinationOrder) {
        const refundLine = refundDetail.line;
        const alreadyRefundedLots = refundLine.refund_orderline_ids
            .filter((item) => !["cancel", "draft"].includes(item.order_id.state))
            .flatMap((item) => item.pack_lot_ids)
            .map((pack_lot) => pack_lot.lot_name);
        const options = refundLine.pack_lot_ids
            .map((p) => p.lot_name)
            .filter((lotName) => !alreadyRefundedLots.includes(lotName));
        return {
            ...super.getRefundLinesDetails(refundDetail, destinationOrder),
            // Only include as many pack_lot_ids as the refunded quantity requires.
            pack_lot_ids: options
                .slice(0, refundDetail.qty)
                .map((lotName) => ["create", { lot_name: lotName }]),
        };
    },
});
