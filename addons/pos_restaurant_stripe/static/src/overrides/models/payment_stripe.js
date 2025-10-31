import { PaymentStripe } from "@pos_stripe/app/payment_stripe";
import { patch } from "@web/core/utils/patch";

patch(PaymentStripe.prototype, {
    async captureAfterPayment(processPayment, line) {
        // Don't capture if the customer can tip, in that case we
        // will capture later.
        if (!this.canBeAdjusted(line.uuid)) {
            return super.captureAfterPayment(...arguments);
        }
    },

    async sendPaymentAdjust(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        this.capturePaymentStripe(line.transaction_id, line.amount, {
            stripe_currency_rounding: line.currency_id.rounding,
        });
    },

    canBeAdjusted(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        return (
            this.pos.config.set_tip_after_payment &&
            line.payment_method_id.use_payment_terminal === "stripe" &&
            line.card_type !== "interac" &&
            (!line.card_type || !line.card_type.includes("eftpos"))
        );
    },
});
