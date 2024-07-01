import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ADYEN_LATEST_RESPONSE", () => {
            this.getPendingPaymentLine(
                "adyen"
<<<<<<< HEAD
            ).payment_method_id.payment_terminal.handleAdyenStatusResponse();
||||||| parent of c1e42cb32d2f (temp)
            this.pos
                .getPendingPaymentLine("adyen")
                .payment_method.payment_terminal.handleAdyenStatusResponse();
=======
            ).payment_method.payment_terminal.handleAdyenStatusResponse();
>>>>>>> c1e42cb32d2f (temp)
        });
    },
});
