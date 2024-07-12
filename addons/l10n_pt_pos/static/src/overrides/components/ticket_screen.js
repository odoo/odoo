/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    async _fetchSyncedOrders() {
        await super._fetchSyncedOrders(...arguments);
        if (!this.pos.isPortugueseCompany()) {
            return;
        }
        // Refresh this till's orders from the server, which invoices them (FS, FR, NC) at sync.
        // An order not synced yet has a local id the server does not know.
        const configId = this.pos.config.id;
        const syncedIds = this.pos.models["pos.order"]
            .getAll()
            .filter((order) => order.config_id?.id === configId && order.isSynced)
            .map((order) => order.id);
        if (syncedIds.length) {
            await this.pos.data.read("pos.order", syncedIds);
        }
    },
});
