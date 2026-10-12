import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

patch(PosPayment.prototype, {
    getQrPopupProps() {
        const base = super.getQrPopupProps();
        const lang = this.pos_order_id?.user_id?.lang?.split("_")?.[0];
        const supportedLanguages = ["fr", "nl"];
        const frameLanguage = lang && supportedLanguages.includes(lang) ? lang : "fr";
        return { ...base, frameLanguage };
    },

    handlePaymentResponse(isPaymentSuccessful) {
        if (this.payment_provider !== "bancontact_pay") {
            return super.handlePaymentResponse(...arguments);
        }

        if (isPaymentSuccessful) {
            this.setPaymentStatus("waitingScan");
        } else {
            this.setPaymentStatus("retry");
        }
        // Force the payment to fail to avoid auto-validating the order.
        // The payment success/failure will be handled by the Bancontact webhook - bancontact_pay_webhook
        return false;
    },

    forceDone() {
        super.forceDone(...arguments);
        if (this.payment_provider === "bancontact_pay") {
            this.qr_code = false;
        }
    },

    forceCancel() {
        super.forceCancel(...arguments);
        if (this.payment_provider === "bancontact_pay") {
            this.bancontact_id = false;
            this.qr_code = false;
        }
    },
});
