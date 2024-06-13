import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/self_order_service";
import { Stripe, StripeError } from "@pos_self_order_stripe/app/stripe";

patch(SelfOrder.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.stripeState = "not_connected";

        const stripePaymentMethod = this.models["pos.payment.method"].find(
            (p) => p.use_payment_terminal === "stripe"
        );

        if (stripePaymentMethod) {
            this.stripe = new Stripe(
                this.env,
                stripePaymentMethod,
                this.access_token,
                this.pos_config_id,
                this.handleStripeError.bind(this),
                this.handleReaderConnection.bind(this)
            );
        }
    },
    handleReaderConnection(state) {
        this.stripeState = state.status;
    },
    handleStripeError(error) {
        this.paymentError = true;
        this.handleErrorNotification(error);
    },
    handleErrorNotification(error) {
        let message = "";

        if (error.code) {
            message = `Error: ${error.code}`;
        } else if (error instanceof StripeError) {
            message = `Stripe: ${error.message}`;
        } else {
            super.handleErrorNotification(...arguments);
            return;
        }

        this.notification.add(message, {
            type: "danger",
        });
    },
});
