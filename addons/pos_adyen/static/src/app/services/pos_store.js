import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("ADYEN_LATEST_RESPONSE", ({ payment_method_id }) => {
            if (!this.getPendingPaymentLine("adyen")) {
                return;
            }
            const paymentMethod = this.models["pos.payment.method"].get(payment_method_id);
            paymentMethod?.payment_terminal?.handleAdyenStatusResponse();
        });
    },
});
