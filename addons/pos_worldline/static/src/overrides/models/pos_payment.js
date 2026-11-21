import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState = {
            ...this.uiState,
            worldlineExchangeId: null,
        };
    },

    setPaymentStatus(value) {
        super.setPaymentStatus(...arguments);
        // Avoid blocking transaction after "force cancel"
        if (value === "retry" && this.payment_method_id?.use_payment_terminal === "worldline_api") {
            this.payment_method_id.payment_terminal?.releasePendingTransaction(this);
        }
    },
});
