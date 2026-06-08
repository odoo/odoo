import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    get showBancontact() {
        return (
            this.selectedPaymentMethod.payment_provider === "bancontact_pay" && this.state.qrCode
        );
    },

    get amount() {
        return this.selfOrder.formatMonetary(this.selfOrder.currentOrder.amount_total, {
            currencyId: this.selfOrder.currency,
        });
    },

    get frameLanguage() {
        const lang = this.selfOrder.currentLanguage?.code?.split("_")?.[0];
        return ["fr", "nl"].includes(lang) ? lang : "fr";
    },

    async startPayment() {
        // Already waiting bancontact payment, do not start another one
        const payments = this.selfOrder.currentOrder.payment_ids;
        const waitingBancontactPayment = payments.find(
            (p) =>
                p.payment_method_id.id === this.state.paymentMethodId &&
                p.payment_method_id.payment_provider === "bancontact_pay" &&
                p.bancontact_id &&
                p.qr_code &&
                ["waiting", "waitingScan", "waitingCancel"].includes(p.payment_status)
        );
        if (waitingBancontactPayment) {
            if (waitingBancontactPayment.amount === this.selfOrder.currentOrder.amount_total) {
                this.state.qrCode = waitingBancontactPayment.qr_code;
                return;
            }
            this.selfOrder.currentOrder.removePaymentline(waitingBancontactPayment);
        }
        await super.startPayment(...arguments);
    },
});
