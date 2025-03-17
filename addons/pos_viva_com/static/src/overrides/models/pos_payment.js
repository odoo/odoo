import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    updateRefundPaymentLine(refundedPaymentLine) {
        super.updateRefundPaymentLine(refundedPaymentLine);
        this.vivaComParentSessionId = refundedPaymentLine?.viva_com_session_id;
    },
});
