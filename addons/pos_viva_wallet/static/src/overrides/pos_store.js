import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("VIVA_WALLET_LATEST_RESPONSE", (payload) => {
            if (payload.config_id === this.config.id) {
                const paymentLine = this.models["pos.payment"].find(
                    (line) => line.uiState.vivaSessionId === payload.session_id
                );

                if (
                    paymentLine &&
                    !paymentLine.is_done() &&
                    paymentLine.get_payment_status() !== "retry"
                ) {
                    paymentLine.payment_method_id.payment_terminal.handleVivaWalletStatusResponse(
                        paymentLine,
                        payload
                    );
                }
            }
        });
    },
});
