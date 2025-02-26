import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "viva_wallet" &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "pending"
            );
            if (!pendingPaymentLine) {
                return;
            }
        });
    },
    async addNewPaymentLine(paymentMethod) {
        if (paymentMethod.use_payment_terminal === "viva_wallet" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            if (!refundedOrder) {
                return;
            }
            const sessionIds = this.currentOrder.payment_ids.map(
                (pi) => pi.uiState.viva_wallet_session
            );
            const vivaWalletPaymentline = refundedOrder.payment_ids.find(
                (pi) =>
                    pi.payment_method_id.use_payment_terminal === "viva_wallet" &&
                    !sessionIds.find((x) => x === pi.viva_wallet_session)
            );
            const currentDue = this.currentOrder.getDue();
            if (!vivaWalletPaymentline || this.currentOrder.currency.isZero(currentDue)) {
                this.pos.notification.add(
                    _t(
                        "Adding a new Viva wallet payment line is not allowed under the current conditions."
                    ),
                    { type: "warning", sticky: false }
                );
                return false;
            }
            const res = await super.addNewPaymentLine(paymentMethod);
            const newPaymentLine = this.paymentLines.at(-1);
            const amountToSet = Math.min(
                Math.abs(newPaymentLine.amount),
                vivaWalletPaymentline?.amount
            );
            if (res) {
                newPaymentLine.setAmount(-amountToSet);
                newPaymentLine.updateRefundPaymentLine(vivaWalletPaymentline);
            }
            return res;
        } else {
            return await super.addNewPaymentLine(paymentMethod);
        }
    },
});
