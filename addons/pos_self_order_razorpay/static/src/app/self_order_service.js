/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { Razorpay, RazorpayError } from "@pos_self_order_razorpay/app/razorpay";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);

        const razorpayPaymentMethod = this.pos_payment_methods.find(
            (p) => p.use_payment_terminal === "razorpay"
        );

        if (razorpayPaymentMethod) {
            this.razorpay = new Razorpay(
                this.env,
                razorpayPaymentMethod,
                this.access_token,
                this.pos_config_id,
                this.handleRazorpayError.bind(this),
            );
        }
    },

    handleRazorpayError(error, type) {
        this.paymentError = true;
        this.handleErrorNotification(error, type);
    },

    handleErrorNotification(error, type = "danger") {
        let errorMessage = ""
        if (error instanceof RazorpayError) {
            errorMessage = `Razorpay POS: ${error.message}`;
            this.notification.add(errorMessage, {
                type: type,
            });
        } else {
            super.handleErrorNotification(...arguments);
        }
    },
});
