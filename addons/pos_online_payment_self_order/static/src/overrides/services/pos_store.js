import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.printingQueue = [];
        this.data.connectWebSocket("ONLINE_PAYMENT_SUCCESS", (data) => {
            if (document.visibilityState === "visible") {
                this.printSelfOrderReceipt(data.order_id);
            } else {
                this.printingQueue.push(() => this.printSelfOrderReceipt(data.order_id));
            }
        });

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
            this.printReceipt({ order });
            await this.sendOrderInPreparation(order, { bypassPdis: true });
        } catch (error) {
            console.log(error);
        }
    },
});
