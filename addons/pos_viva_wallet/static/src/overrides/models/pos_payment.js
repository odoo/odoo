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
            viva_wallet_session: null,
        };
    },
    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.viva_wallet_session = refundedPaymentLine?.viva_wallet_session;
    },
});
