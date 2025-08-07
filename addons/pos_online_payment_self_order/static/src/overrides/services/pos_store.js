import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.printingQueue = [];

        if (this.config.self_ordering_mode === "mobile") {
            this.data.connectWebSocket("ONLINE_PAYMENT_STATUS", (notification) => {
                if (notification.status !== "success") {
                    return;
                }

                const orderId = notification.data["pos.order"][0].id;
                if (document.visibilityState === "visible") {
                    this.printSelfOrderReceipt(orderId);
                } else {
                    this.printingQueue.push(() => this.printSelfOrderReceipt(orderId));
                }
            });
        }

        window.addEventListener("visibilitychange", async () => {
            if (document.visibilityState === "visible") {
                while (this.printingQueue.length > 0) {
                    await this.printingQueue.shift()();
                }
            }
        });
    },

    async printSelfOrderReceipt(orderId) {
        try {
            const result = await this.data.callRelated("pos.order", "get_order_to_print", [
                orderId,
            ]);
            const order = result["pos.order"][0];
            await this.printReceipt({ order });
            await this.sendOrderInPreparation(order, { bypassPdis: true });
        } catch {
            console.info("Another instance is already printing the receipt");
        }
    },
});
