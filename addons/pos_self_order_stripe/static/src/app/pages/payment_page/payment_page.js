/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentPage } from "@pos_self_order/app/pages/payment_page/payment_page";

patch(PaymentPage.prototype, {
    async startPayment() {
        this.selfOrder.paymentError = false;
        const paymentMethod = this.selfOrder.pos_payment_methods.find(
            (p) => p.id === this.state.paymentMethodId
        );

        if (paymentMethod.use_payment_terminal === "stripe") {
            await this.selfOrder.stripe.startPayment(this.selfOrder.currentOrder);
        } else {
            await super.startPayment(...arguments);
        }
    },
});
