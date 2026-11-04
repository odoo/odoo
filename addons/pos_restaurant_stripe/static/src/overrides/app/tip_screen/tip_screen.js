import { TipScreen } from "@pos_restaurant/app/tip_screen/tip_screen";

import { patch } from "@web/core/utils/patch";

patch(TipScreen.prototype, {
    async validateTip() {
        // Since we don't have any tip amount, we never send a capture request to Stripe.
        // This means we need to manually capture the payment here if the tip amount is 0 or invalid,
        // otherwise the order will be left in a "pending" state in Stripe and automatically cancelled.
        if (!this.env.utils.parseValidFloat(this.state.inputTipAmount)) {
            const paymentline = this.pos.get_order().payment_ids[0];
            if (
                paymentline.payment_method_id.use_payment_terminal === "stripe" &&
                paymentline.payment_method_id.payment_terminal
            ) {
                await paymentline.payment_method_id.payment_terminal.capturePayment(
                    paymentline.transaction_id
                );
            }
        }
        return super.validateTip(...arguments);
    },
});
