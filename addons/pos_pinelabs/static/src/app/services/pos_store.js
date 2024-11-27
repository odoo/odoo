import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("PINELABS_PAYMENT_RESPONSE", async (response) => {
            const waitingPaymentLine = this.getPendingPaymentLine("pinelabs");
            if (waitingPaymentLine) {
                waitingPaymentLine.payment_method_id.payment_terminal.handlePinelabsPaymentResponse(
                    response
                );
            }
        });
    },
});
