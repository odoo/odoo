import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("ADYEN_LATEST_RESPONSE", () => {
            this.getPendingPaymentLine(
                "adyen"
<<<<<<< saas-17.4
            ).payment_method_id.payment_terminal.handleAdyenStatusResponse();
||||||| a1a0dff03b52bb3ce23f163f435985bbc4ba4f3e
            this.pos
                .getPendingPaymentLine("adyen")
                .payment_method.payment_terminal.handleAdyenStatusResponse();
=======
            ).payment_method.payment_terminal.handleAdyenStatusResponse();
>>>>>>> d0957749dc775c6b1540d741549e98f80a961575
        });
    },
});
