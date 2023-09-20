/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ADYEN_LATEST_RESPONSE", () => {
            this.pos
                .getPendingPaymentLine("adyen")
                .payment_method.payment_terminal.handleAdyenStatusResponse();
        });
    },
});
