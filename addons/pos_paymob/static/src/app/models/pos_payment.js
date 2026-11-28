import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(vals);
        this.uiState = {
            ...this.uiState,
            paymobRefundTransactionId: null,
            paymobOrderId: null,
            paymobMerchantOrderId: null,
            paymobAmountCents: null,
        };
    },

    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.paymobRefundTransactionId = refundedPaymentLine?.transaction_id;
    },
});
