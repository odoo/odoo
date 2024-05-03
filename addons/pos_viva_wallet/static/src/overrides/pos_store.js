import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("VIVA_WALLET_LATEST_RESPONSE", () => {
            this.getPendingPaymentLine(
                "viva_wallet"
            ).payment_method_id.payment_terminal.handleVivaWalletStatusResponse();
        });
    },
});
