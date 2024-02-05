/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

patch(FloorScreen.prototype, {
    async onMounted() {
        super.onMounted(...arguments);
        await this.pos._fetchDeliverooOrderCount();
    },
    async showDeliverooOrders() {
        const searchDetails = { fieldName: "RECEIPT_NUMBER", searchTerm: "Deliveroo" };
        if (this.pos.shouldLoadOrders()) {
            try {
                this.pos.setLoadingOrderState(true);
                const domain = [
                    ["config_id", "=", this.pos.config.id],
                    ["state", "=", "paid"],
                ];
                const message = await this.pos._syncAllOrdersFromServer(domain);
                if (message) {
                    this.notification.add(message, 5000);
                }
            } finally {
                this.pos.setLoadingOrderState(false);
                this.pos.showScreen("TicketScreen", {
                    ui: { filter: "DELIVERY", searchDetails },
                });
            }
        } else {
            this.pos.showScreen("TicketScreen", {
                ui: { filter: "DELIVERY", searchDetails },
            });
        }
    },
    get deliverooOrderCount() {
        return this.pos.delivery_order_count.deliveroo.awaiting > 0
            ? this.pos.delivery_order_count.deliveroo.awaiting
            : this.pos.delivery_order_count.deliveroo.preparing > 0
            ? this.pos.delivery_order_count.deliveroo.preparing
            : 0;
    },
    get deliverooOrderCountClass() {
        return {
            "d-none":
                !this.pos.delivery_order_count.deliveroo.awaiting &&
                !this.pos.delivery_order_count.deliveroo.preparing,
            "text-bg-danger": this.pos.delivery_order_count.deliveroo.awaiting,
            "text-bg-info": false, //scheduled orders TODO later,
            "text-bg-dark":
                !this.pos.delivery_order_count.deliveroo.awaiting &&
                this.pos.delivery_order_count.deliveroo.preparing,
        };
    },
});
