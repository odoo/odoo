import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(vals);
        this.uiState = {
            ...this.uiState,
            // Original sale's transaction id, sent to Paymob's refund endpoint.
            paymobRefundTransactionId: null,
            // Paymob order registered for this sale; its callback must carry the same order.id.
            paymobOrderId: null,
        };
    },

    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.paymobRefundTransactionId = refundedPaymentLine?.transaction_id;
    },
});
