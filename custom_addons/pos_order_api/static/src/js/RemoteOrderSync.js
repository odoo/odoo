/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        
        // Listen for remote orders on the session channel
        // Note: PosStore already has this.bus (bus_service)
        this.bus.addChannel(`pos_session_${this.session.id}`);
        this.bus.subscribe("NEW_REMOTE_ORDER", (data) => {
            this._onNewRemoteOrder(data);
        });
    },

    async _onNewRemoteOrder(data) {
        console.log("New Remote Order Received:", data);
        
        try {
            // Use native loadServerOrders to fetch and integrate the order
            // This handles lines, partial payments (if any), and reactivity automatically in Odoo 19
            await this.data.loadServerOrders([["id", "=", data.order_id]]);

            // Notify the user via the notification service
            this.notification.add(`New Remote Order: ${data.source === 'uber' ? 'Uber Eats' : 'Online'}`, {
                title: "Remote Order Received",
                type: "info",
                sticky: false,
            });

            // Trigger a sound if needed (optional but nice for kitchen/POS)
            if (this.sound) {
                this.sound.play("bell");
            }

        } catch (e) {
            console.error("Failed to sync remote order:", e);
        }
    }
});
