import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(vals);
        this.uiState = {
            ...this.uiState,
            // Original sale's transaction id, sent to Paymob's refund endpoint.
            paymobRefundTransactionId: null,
            // Original sale's uuid; the refund callback routes back on it (no parent link).
            paymobRefundOrderUuid: null,
        };
    },

    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.paymobRefundTransactionId = refundedPaymentLine?.transaction_id;
        this.uiState.paymobRefundOrderUuid = refundedPaymentLine?.pos_order_id?.uuid;
    },
});
