/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async _fetchSyncedOrders() {
        // When opening the refund screen for instance, we need to mark all cached orders
        // as not up to date, so that we fetch the latest names provided by the backend.
        if (!this.pos.isPortugueseCompany()) {
            return super._fetchSyncedOrders(...arguments);
        }
        const cachedOrders = this.pos.models["pos.order"].getAll();
        const regex = /[^/^]+\/[0-9]+/;
        const idsNotUpToDate = [];
        for (const order of cachedOrders) {
            if (!order || !order.name.match(regex)) {
                let orderId = order.id;
                if (typeof orderId === "string" && orderId.startsWith("pos.order_")) {
                    orderId = parseInt(orderId.replace("pos.order_", ""));
                }
                idsNotUpToDate.push(orderId);
            }
        }
        if (idsNotUpToDate.length > 0) {
            await this.pos.data.read("pos.order", Array.from(new Set(idsNotUpToDate)));
        }
    },
});
