import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    initState() {
        super.initState(...arguments);
        this.uiState = {
            ...this.uiState,
            worldlineExchangeId: null,
        };
    },

    setPaymentStatus(value) {
        super.setPaymentStatus(...arguments);
        // Avoid blocking transaction after "force cancel"
        if (value === "retry" && this.payment_provider === "worldline_api") {
            this.payment_interface?.releasePendingTransaction(this);
        }
    },
});
