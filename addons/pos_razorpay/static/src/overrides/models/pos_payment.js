import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    /**
     * override
     */
    setup(vals) {
        super.setup(vals);
        this.uiState = {
            ...this.uiState,
            transaction_id: null,
            razorpay_p2p_request_id: null,
        };
    },
    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.transaction_id = refundedPaymentLine?.transaction_id;
        this.uiState.razorpay_p2p_request_id = refundedPaymentLine?.razorpay_p2p_request_id;
    },
});
