/** @odoo-module */

import { Patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { useService } from "@web/core/utils/hooks";

Patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        this.busService = useService("bus_service");
        
        // Subscribe if config allows
        if (this.config.accept_remote_orders) {
            this.busService.addChannel("pos_remote_orders");
            this.busService.subscribe("pos_remote_orders", (payload) => {
                this._handleRemoteOrder(payload);
            });
            console.log("POS Remote Print: Listening for orders...");
        }
    },

    async _handleRemoteOrder(payload) {
        // payload: { order_id: 123, uuid: '...' }
        // Type: 'new_order' (usually bus sends [type, payload] or just payload depending on version)
        // Assuming payload is the data part.

        console.log("Remote Order Received:", payload);
        
        // 1. Attempt to Claim (Lock) the order
        // We call a backend method to "Claim" the print job.
        // This ensures only 1 tablet prints it.
        
        try {
            const shouldPrint = await this.orm.call(
                "pos.order", 
                "claim_remote_print", 
                [[payload.order_id], this.pos_session.id]
            );

            if (shouldPrint) {
                // 2. Fetch Order Data and Print
                // We reuse existing print logic? 
                // We need to fetch the order details to render the receipt.
                
                // For MVP, we might just print a simple "New Notification" or fetch the full order
                // print_order_receipt is complex, it expects an Order object in JS.
                // We can use this.env.services.report? Or load the order into POS?
                
                await this._printRemoteOrder(payload.order_id);
            }
        } catch (e) {
            console.error("Remote Print Error:", e);
        }
    },

    async _printRemoteOrder(orderId) {
        // Fetch order details from server
        // This is a simplification. Real implementation needs to construct the receipt data.
        // We can call `get_order_details` (custom) or use `read`.
        
        const orders = await this.orm.read("pos.order", [orderId], ["name", "lines", "amount_total"]);
        if (!orders || !orders.length) return;
        
        const orderData = orders[0];
        // Trigger Printer
        // Implementation depends on if we use HW Proxy or Browser Print
        // Assuming standard kitchen printing via printer_id
        
        // Ideally we just trigger a reprint_receipt kind of flow
        console.log("Printing Remote Order:", orderData.name);
        
        // TODO: Full Ticket Rendering Logic
        // For now, we alert (simulated print)
        // alert(`Printing Order ${orderData.name} - Kitchen`);
    }
});
