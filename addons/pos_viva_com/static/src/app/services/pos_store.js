import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("VIVA_COM_LATEST_RESPONSE", (payload) => {
            if (payload.config_id === this.config.id) {
                const paymentLine = this.models["pos.payment"].find(
                    (line) => line.uiState.vivaSessionId === payload.session_id
                );

                if (
                    paymentLine &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "retry"
                ) {
                    paymentLine.payment_method_id.payment_terminal.handleVivaComStatusResponse(
                        paymentLine,
                        payload
                    );
                }
            }
        });
    },
});
