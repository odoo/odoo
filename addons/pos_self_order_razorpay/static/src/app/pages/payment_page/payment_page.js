import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async startPayment() {
        this.selfOrder.paymentError = false;
        const paymentMethod = this.selfOrder.models["pos.payment.method"].find(
            (p) => p.id === this.state.paymentMethodId
        );

        if (paymentMethod.use_payment_terminal === "razorpay") {
            await this.selfOrder.razorpay.startPayment(this.selfOrder.currentOrder);
        } else {
            await super.startPayment(...arguments);
        }
    },
});
