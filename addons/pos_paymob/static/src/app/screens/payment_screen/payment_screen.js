import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.use_payment_terminal === "paymob" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            if (!refundedOrder) {
                return false;
            }
            // An original Paymob line on the refunded order not yet claimed by another refund.
            const usedTransactions = this.currentOrder.payment_ids.map(
                (pi) => pi.uiState.paymobRefundTransactionId
            );
            const paymobPaymentLine = refundedOrder.payment_ids.find(
                (pi) =>
                    pi.payment_method_id.use_payment_terminal === "paymob" &&
                    pi.transaction_id &&
                    !usedTransactions.includes(pi.transaction_id)
            );
            if (!paymobPaymentLine || this.currentOrder.remainingDue === 0) {
                this.pos.notification.add(
                    _t(
                        "Adding a new Paymob refund line is not allowed under the current conditions."
                    ),
                    { type: "warning" }
                );
                return false;
            }
            const res = await super.addNewPaymentLine(...arguments);
            if (res) {
                const newPaymentLine = this.paymentLines.at(-1);
                const amountToSet = Math.min(
                    Math.abs(newPaymentLine.amount),
                    paymobPaymentLine.amount
                );
                newPaymentLine.setAmount(-amountToSet);
                newPaymentLine.updateRefundPaymentLine(paymobPaymentLine);
            }
            return res;
        }
        return super.addNewPaymentLine(...arguments);
    },
});
