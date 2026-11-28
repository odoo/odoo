import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        // Not getPendingPaymentLine: it skips cancelled lines the customer can still pay.
        const getOpenPaymobLines = () =>
            this.models["pos.payment"].filter(
                (line) =>
                    line.payment_method_id.use_payment_terminal === "paymob" &&
                    line.payment_method_id.payment_terminal.isPaymobLineOpen(line)
            );
        this.data.connectWebSocket("PAYMOB_LATEST_RESPONSE", (payload) => {
            if (payload.config_id !== this.config.id) {
                return;
            }
            for (const line of getOpenPaymobLines()) {
                line.payment_method_id.payment_terminal.checkPaymobPaymentStatus(line);
            }
        });
        for (const line of getOpenPaymobLines()) {
            line.payment_method_id.payment_terminal.pollPaymobPaymentStatus(line);
        }
    },
});
