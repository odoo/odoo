import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

patch(PosPayment.prototype, {
    initState() {
        super.initState();
        this.uiState.bancontactIdempotencyKey = null;
    },

    getQrPopupProps() {
        const base = super.getQrPopupProps();
        const lang = this.pos_order_id?.user_id?.lang?.split("_")?.[0];
        const supportedLanguages = ["fr", "nl"];
        const frameLanguage = lang && supportedLanguages.includes(lang) ? lang : "fr";
        return { ...base, frameLanguage };
    },

    get isBancontactRefund() {
        return (
            this.payment_provider === "bancontact_pay" &&
            Boolean(this.bancontact_refunded_payment_id)
        );
    },

    get isBancontactRefundPending() {
        return Boolean(this.bancontact_refund_id) && this.payment_status === "waiting";
    },

    get isBancontactRefundSent() {
        return (
            Boolean(this.bancontact_refund_id) && ["waiting", "done"].includes(this.payment_status)
        );
    },

    setBancontactRefundStatus(refundStatus) {
        if (refundStatus === "FAILED") {
            this.uiState.bancontactIdempotencyKey = null;
        }
        this.setPaymentStatus(this.payment_interface.refundToPaymentStatus(refundStatus));
    },

    handlePaymentResponse(isPaymentSuccessful) {
        if (this.payment_provider !== "bancontact_pay") {
            return super.handlePaymentResponse(...arguments);
        }
        if (this.isBancontactRefund) {
            // `isPaymentSuccessful` is the Bancontact refund status, or false if the request failed
            if (isPaymentSuccessful) {
                this.setBancontactRefundStatus(isPaymentSuccessful);
            } else {
                this.setPaymentStatus(undefined);
            }
            // A pending refund isn't successful yet: its success/failure will be handled by `checkRefundStatus`
            return this.payment_status === "done";
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
