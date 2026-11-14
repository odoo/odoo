import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { status } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    onMounted() {
        const result = super.onMounted(...arguments);
        this._waitForResumedWorldlinePayments();
        return result;
    },

    /**
     * Validate Worldline payments after webpage refresh
     */
    async _waitForResumedWorldlinePayments() {
        for (const line of this.paymentLines) {
            const resumedPayment =
                line.payment_method_id.payment_terminal?.resumedPayments?.[line.uuid];
            if (!resumedPayment) {
                continue;
            }
            this.pos.paymentTerminalInProgress = true;
            const isPaymentSuccessful = await resumedPayment;
            this.pos.paymentTerminalInProgress = false;
            const currentOrder = line.pos_order_id;
            if (
                status(this) === "mounted" &&
                isPaymentSuccessful &&
                currentOrder.isPaid() &&
                this.pos.config.auto_validate_terminal_payment &&
                !currentOrder.isRefundInProcess()
            ) {
                this.validateOrder(false);
            }
        }
    },
});
