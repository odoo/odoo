import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState = {
            ...(this.uiState ?? {}),
            adyenRefundTransactionId: null,
            adyenRefundTransactionTimestamp: null,
        };
    },

    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        if (refundedPaymentLine) {
            this.uiState.adyenRefundTransactionTimestamp = refundedPaymentLine.create_date
                .toUTC()
                .toISO();
            this.uiState.adyenRefundTransactionId = refundedPaymentLine.transaction_id;
        }
    },

    setTerminalServiceId(id) {
        this.terminalServiceId = id;
    },
});
