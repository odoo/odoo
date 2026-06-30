import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async makePaymentRequest() {
        this.selfOrder.paymentError = false;
        try {
            return await rpc(`/kiosk/payment/${this.selfOrder.config.id}/kiosk`, {
                order: this.selfOrder.currentOrder.serializeForORM(),
                access_token: this.selfOrder.access_token,
                payment_method_id: this.state.paymentMethodId,
            });
        } catch (error) {
            this.selfOrder.handleErrorNotification(error);
            this.selfOrder.paymentError = true;
            return false;
        }
    },

    async pollVivaPayment(vivaSessionId) {
        const paymentFinished = await rpc("/pos_self_order_viva_com/poll_payment", {
            access_token: this.selfOrder.access_token,
            payment_method_id: this.state.paymentMethodId,
            viva_session_id: vivaSessionId,
        });
        if (!paymentFinished) {
            setTimeout(() => this.pollVivaPayment(vivaSessionId), 5000);
        }
    },

    async startPayment() {
        if (this.selectedPaymentMethod.use_payment_terminal !== "viva_com") {
            return super.startPayment(...arguments);
        }

        const vivaSessionId = (await this.makePaymentRequest())?.payment_status;
        if (vivaSessionId) {
            setTimeout(() => this.pollVivaPayment(vivaSessionId), 5000);
        }
    },
});
