import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";
import { BancontactRefundPopup } from "@pos_bancontact_pay/app/bancontact_refund_popup/bancontact_refund_popup";

patch(PaymentScreen.prototype, {
    get bancontactPaymentMethod() {
        return this.payment_methods_from_config.find(
            (method) => method.payment_provider === "bancontact_pay"
        );
    },

    get showBancontactRefund() {
        return this.isRefundOrder && Boolean(this.bancontactPaymentMethod);
    },

    async getBancontactRefundableLines() {
        const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
        const payments = (refundedOrder?.payment_ids || []).filter(
            (payment) =>
                payment.payment_provider === "bancontact_pay" &&
                payment.payment_method_id.bancontact_refund_enabled &&
                payment.bancontact_id &&
                payment.isDone()
        );
        await this.refreshBancontactRefundStatus(payments);

        return payments.map((payment) => {
            const amountRefunded = payment.bancontact_refund_ids
                .filter((refund) => refund.isBancontactRefundSent)
                .reduce((total, refund) => total + Math.abs(refund.amount), 0);
            const amountLeft = this.pos.currency.round(payment.amount - amountRefunded);
            return {
                id: payment.id,
                payment,
                payment_method_name: payment.payment_method_id.name,
                amount: payment.amount,
                amount_left: amountLeft,
                fully_refunded: !this.pos.currency.isPositive(amountLeft),
            };
        });
    },

    async refreshBancontactRefundStatus(payments) {
        const pendingRefunds = payments
            .flatMap((payment) => payment.bancontact_refund_ids)
            .filter((refund) => refund.isBancontactRefundPending);
        const refundsByMethod = Map.groupBy(pendingRefunds, (refund) => refund.payment_method_id);
        for (const [method, refunds] of refundsByMethod) {
            try {
                await method.payment_interface.checkRefundStatus(refunds);
            } catch {
                this.notification.add(
                    _t("The status of the pending Bancontact refunds couldn't be refreshed."),
                    { type: "warning" }
                );
            }
        }
    },

    getBancontactRefundLine(payment) {
        return this.paymentLines.find(
            (line) =>
                line.bancontact_refunded_payment_id?.id === payment.id &&
                !line.isBancontactRefundSent
        );
    },

    async onClickBancontactRefund() {
        const lines = await this.getBancontactRefundableLines();
        if (lines.every((line) => line.fully_refunded)) {
            return;
        }

        let refunds;
        if (lines.length === 1) {
            refunds = [{ payment: lines[0].payment, amount: lines[0].amount_left }];
        } else {
            const amounts = {};
            for (const line of lines) {
                const refundLine = this.getBancontactRefundLine(line.payment);
                if (refundLine) {
                    amounts[line.id] = Math.abs(refundLine.amount);
                }
            }
            refunds = await makeAwaitable(this.dialog, BancontactRefundPopup, {
                lines,
                amounts,
            });
            if (!refunds) {
                return;
            }
        }

        for (const { payment, amount } of refunds) {
            const refundLine = this.getBancontactRefundLine(payment);
            if (refundLine && amount > 0) {
                refundLine.setAmount(-amount);
            } else if (refundLine) {
                this.currentOrder.removePaymentline(refundLine);
            } else if (amount > 0) {
                const result = this.currentOrder.addPaymentline(payment.payment_method_id);
                if (result.status) {
                    result.data.setAmount(-amount);
                    result.data.bancontact_refunded_payment_id = payment;
                }
            }
        }
        this.numberBuffer.reset();
    },
});
