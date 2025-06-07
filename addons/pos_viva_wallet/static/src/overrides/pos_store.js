import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("VIVA_WALLET_LATEST_RESPONSE", () => {
            const pendingLine = this.getPendingPaymentLine("viva_wallet");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleVivaWalletStatusResponse();
            }
        });
    },
});
