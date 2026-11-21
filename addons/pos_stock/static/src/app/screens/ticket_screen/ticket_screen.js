import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    getRefundLinesDetails(refundDetail, destinationOrder) {
        const refundLine = refundDetail.line;
        const alreadyRefundedLots = refundLine.refund_orderline_ids
            .filter((item) => !["cancel", "draft"].includes(item.order_id.state))
            .flatMap((item) => item.pack_lot_ids)
            .map((pack_lot) => pack_lot.lot_name);
        const options = refundLine.pack_lot_ids.filter(
            (p) => !alreadyRefundedLots.includes(p.lot_name)
        );
        return {
            ...super.getRefundLinesDetails(refundDetail, destinationOrder),
            pack_lot_ids: options.slice(0, refundDetail.qty).map((p) => [
                "create",
                {
                    lot_name: p.lot_name,
                    expiration_date: p.expiration_date || false,
                },
            ]),
        };
    },
});
