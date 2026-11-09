import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async settleTip(order, amount) {
        const line = order.adjustableTipLine;
        // Stripe captures through the tip adjustment, which the core skips for a zero tip
        if (
            !amount &&
            !order.uiState.pendingTipArgs &&
            line?.payment_method_id.payment_provider === "stripe" &&
            !(await line.payment_interface.capturePayment(line.transaction_id))
        ) {
            return false;
        }
        return super.settleTip(...arguments);
    },
});
