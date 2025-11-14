import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState = {
            ...(this.uiState ?? {}),
            vivaSessionId: null,
            vivaComParentSessionId: null,
        };
    },

    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.uiState.vivaComParentSessionId = refundedPaymentLine?.viva_com_session_id;
    },
});
