import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("VIVA_WALLET_LATEST_RESPONSE", () => {
            const pendingLine = this.getPendingPaymentLine("viva_wallet");

            if (pendingLine) {
                pendingLine.payment_method_id.payment_terminal.handleVivaWalletStatusResponse();
            }
        });
    },
});
