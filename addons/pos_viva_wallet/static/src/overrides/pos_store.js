/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("VIVA_WALLET_LATEST_RESPONSE", () => {
            const pendingLine = this.pos.getPendingPaymentLine("viva_wallet");

            if (pendingLine) {
                pendingLine.payment_method.payment_terminal.handleVivaWalletStatusResponse();
            }
        });
    },
});
