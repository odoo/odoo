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
            const resumedPayment = line.payment_interface?.resumedPayments?.[line.uuid];
            if (!resumedPayment) {
                continue;
            }
            const isPaymentSuccessful = await resumedPayment;
            if (status(this) === "mounted" && isPaymentSuccessful) {
                await this.pos.autoValidateOrder({ order: line.pos_order_id });
            }
        }
    },
});
