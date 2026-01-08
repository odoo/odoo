import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("MOLLIE_PAYMENT_STATUS", (payload) => {
            if (payload.session_id === this.session.id) {
                const paymentLine = this.models["pos.payment"].find(
                    (line) => line.transaction_id === payload.payment_id
                );

                if (
                    paymentLine &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "retry"
                ) {
                    paymentLine.payment_method_id.payment_terminal.handleMollieStatusResponse(
                        paymentLine,
                        payload
                    );
                }
            }
        });
    },
});
