import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { patch } from "@web/core/utils/patch";

patch(TipScreen.prototype, {
    async validateTip() {
        const line = this.adjustableTipLine;
        // Stripe captures through the tip adjustment, which the core skips for a zero tip
        if (
            !this.pos.parseValidFloat(this.state.inputTipAmount) &&
            this.currentOrder.isSynced &&
            line.payment_method_id.payment_provider === "stripe"
        ) {
            await line.payment_interface.capturePayment(line.transaction_id);
        }
        return super.validateTip(...arguments);
    },
});
