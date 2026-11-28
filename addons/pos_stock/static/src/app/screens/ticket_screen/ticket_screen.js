import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

const { DateTime } = luxon;

patch(TicketScreen.prototype, {
    getOrderSortPriority(order) {
        // Paid orders to pick up today first, so the cashier finds them when the customer comes.
        if (
            order.pickup_later &&
            this.isOrderDoneOrPaid(order) &&
            order.shipping_date?.hasSame(DateTime.now(), "day")
        ) {
            return 1;
        }
        return super.getOrderSortPriority(order);
    },
    async _updateSyncedOrders() {
        await super._updateSyncedOrders(...arguments);
        const config = this.pos.config;
        if (this.state.filter === "SYNCED" && this.state.page === 1 && config.ship_later) {
            // Pickups due today can be older than the first page: load them to list them first.
            await this.pos.data.loadServerOrders([
                ["config_id", "in", [config.id, ...config.raw.trusted_config_ids]],
                ["pickup_later", "=", true],
                ["shipping_date", "=", DateTime.now().toISODate()],
                ["state", "in", ["paid", "done"]],
            ]);
        }
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
