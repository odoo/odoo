import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

patch(PosPayment.prototype, {
    handlePaymentResponse(isPaymentSuccessful) {
        if (this.payment_provider !== "bancontact_pay") {
            return super.handlePaymentResponse(...arguments);
        }

        if (isPaymentSuccessful) {
            this.setPaymentStatus("waitingScan");
            if (this.payment_method_id.bancontact_usage === "display") {
                this.updateCustomerDisplayQrCode(this.qr_code);
            }
        } else {
            this.setPaymentStatus("retry");
        }
        // Force the payment to fail to avoid auto-validating the order.
        // The payment success/failure will be handled by the Bancontact webhook - bancontact_pay_webhook
        return false;
    },

    handlePaymentCancelResponse(isCancelSuccessful) {
        if (isCancelSuccessful) {
            this.updateCustomerDisplayQrCode(null);
        }
        return super.handlePaymentCancelResponse(...arguments);
    },

    forceDone() {
        super.forceDone(...arguments);
        if (this.payment_provider === "bancontact_pay") {
            this.qr_code = false;
            this.updateCustomerDisplayQrCode(null);
        }
    },

    forceCancel() {
        super.forceCancel(...arguments);
        if (this.payment_provider === "bancontact_pay") {
            this.bancontact_id = false;
            this.qr_code = false;
            this.updateCustomerDisplayQrCode(null);
        }
    },
});
