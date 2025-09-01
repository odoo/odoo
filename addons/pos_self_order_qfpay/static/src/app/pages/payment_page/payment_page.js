import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async startPayment() {
        this.selfOrder.paymentError = false;
        const paymentMethod = this.selfOrder.models["pos.payment.method"].find(
            (p) => p.id === this.state.paymentMethodId
        );
        if (paymentMethod.use_payment_terminal === "qfpay") {
            const order = this.selfOrder.currentOrder;
            const response = await this.selfOrder.qfpay.makeQFPayRequest("trade", {
                func_type: 1001,
                amt: order.amount_total,
                channel: paymentMethod.qfpay_payment_type,
                out_trade_no: `${order.uuid}--${order.session_id.id}--${paymentMethod.id}`,
                wait_card_timeout: 30,
                camera_id: 1,
            });
            if (!response) {
                this.selfOrder.paymentError = true;
            }
        } else {
            await super.startPayment(...arguments);
        }
    },
});
