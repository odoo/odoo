import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("PAYMOB_LATEST_RESPONSE", (payload) => {
            if (payload.config_id !== this.config.id) {
                return;
            }
            const pendingLine = this.getPendingPaymentLine("paymob");
            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handlePaymobWebhook();
            }
        });
    },
});
