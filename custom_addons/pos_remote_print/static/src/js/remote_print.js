/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup(env, deps) {
        await super.setup(env, deps);

        // PosStore already has this.bus, this.notification, this.data after setup.
        // Do NOT use useService() here — PosStore is not an OWL component.

        if (this.config && this.config.accept_remote_orders) {
            this.bus.subscribe("NEW_REMOTE_ORDER", (payload) =>
                this._onNewRemoteOrder(payload)
            );
            console.log("POS Remote Print: Listening for NEW_REMOTE_ORDER...");
        }
    },

    async _onNewRemoteOrder(payload) {
        console.log("Remote Order Signal:", payload);
        try {
            const orderId = payload.order_id;

            // Fetch full order data from backend
            const serverData = await this.data.call(
                "pos.order",
                "read_pos_data",
                [[orderId], this.config.id]
            );

            if (
                !serverData ||
                !serverData["pos.order"] ||
                !serverData["pos.order"].length
            ) {
                console.warn("Remote order data empty or not found:", orderId);
                return;
            }

            // Load data into POS Store
            await this.data.loadServerOrders([["id", "=", orderId]]);

            // Get the loaded Order instance
            const order = this.models["pos.order"].get(orderId);

            if (order) {
                this.notification.add(
                    `New ${payload.source} Order: ${order.name}`,
                    {
                        title: "Remote Order Received",
                        type: "info",
                        sticky: false,
                    }
                );

                if (
                    this.config.accept_remote_orders &&
                    order.delivery_status === "received"
                ) {
                    const shouldPrint = await this.data.call(
                        "pos.order",
                        "claim_remote_print",
                        [[order.id], this.session.id]
                    );

                    if (shouldPrint) {
                        console.log(
                            "Printing Remote Order Ticket:",
                            order.name
                        );
                    }
                }
            }
        } catch (e) {
            console.error("Remote Order Sync Failed:", e);
        }
    },
});

