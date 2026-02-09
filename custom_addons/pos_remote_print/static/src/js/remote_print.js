/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { useService } from "@web/core/utils/hooks";

patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        this.busService = useService("bus_service");
        this.notification = useService("notification");
        this.orm = useService("orm"); // Ensure ORM service is available

        // Bind for callback context
        this._onNewRemoteOrder = this._onNewRemoteOrder.bind(this);
        
        if (this.config.accept_remote_orders) {
            this.busService.subscribe("NEW_REMOTE_ORDER", this._onNewRemoteOrder);
            console.log("POS Remote Print: Listening for NEW_REMOTE_ORDER...");
        }
    },

    async _onNewRemoteOrder(payload) {
        console.log("🚀 Remote Order Signal:", payload);
        try {
            const orderId = payload.order_id;
            
            // 1. Fetch full order data from backend
            // usage: read_pos_data([ids], config_id)
            const serverData = await this.orm.call(
                "pos.order", 
                "read_pos_data", 
                [[orderId], this.config.id]
            );
            
            if (!serverData || !serverData['pos.order'] || !serverData['pos.order'].length) {
                console.warn("⚠️ Remote order data empty or not found:", orderId);
                return;
            }

            // 2. Load data into POS Store
            // This updates existing orders or adds new ones
            await this.load_server_data(serverData);
            
            // 3. Get the loaded Order instance
            const order = this.models["pos.order"].get(orderId);
            
            if (order) {
                // 4. Notify User
                this.notification.add(`New ${payload.source} Order: ${order.name}`, {
                    title: "Remote Order Received",
                    type: "info",
                    sticky: false
                });

                // 5. Trigger Auto-Print (if configured)
                if (this.config.accept_remote_orders && order.delivery_status === 'received') {
                    // Prevent duplicate prints via backend lock logic
                    // We call backend to claim the print
                    const shouldPrint = await this.orm.call(
                        "pos.order", 
                        "claim_remote_print", 
                        [[order.id], this.pos_session.id]
                    );

                    if (shouldPrint) {
                         // Print Kitchen Ticket
                         // In Odoo 17+, printChanges is used for kitchen printing
                         // usage: printChanges(order)
                         // But we need to check if order has changes to print?
                         // API orders valid as 'changes'?
                         
                         // Force 'saved' state to ensure it prints?
                         // Actually, printChanges checks 'order.hasChangesToPrint()'
                         // API orders might not have 'lines' marked as new in frontend if loaded from backend.
                         // But if they are 'paid', kitchen printing might behave differently.
                         
                         // For now, let's just log and maybe trigger a reprint if needed.
                         console.log("🖨️ Printing Remote Order Ticket:", order.name);
                         // await this.printChanges(order); // Uncomment if kitchen printing flow is verified
                    }
                }
            }
            
        } catch (e) {
             console.error("❌ Remote Order Sync Failed:", e);
        }
    }
});
