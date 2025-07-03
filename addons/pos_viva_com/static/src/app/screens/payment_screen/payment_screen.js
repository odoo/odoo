import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillStart } from "@odoo/owl";
import { useVivaApp } from "../../hooks/use_viva_app";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(() => {
            const pendingPaymentLine = this.currentOrder.payment_ids.find(
                (paymentLine) =>
                    paymentLine.payment_method_id.use_payment_terminal === "viva_com" &&
                    !paymentLine.isDone() &&
                    paymentLine.getPaymentStatus() !== "pending"
            );
            if (!pendingPaymentLine) {
                return;
            }
        });

        this.vivaApp = useVivaApp(this.validateOrder.bind(this));
        onWillStart(async () => {
            await this.vivaApp.process();
        });
    },
    async addNewPaymentLine(pm) {
        if (this.vivaApp.use(pm)) {
            const previousAnswer = window.localStorage.getItem("vivawallet_app_answer");
            if (previousAnswer === null) {
                await makeAwaitable(this.dialog, ConfirmationDialog, {
                    title: _t("Viva Wallet Application"),
                    body: _t(
                        "Is the vivawallet application installed on your device? If so, the payment will initialize directly from it."
                    ),
                    cancelLabel: _t("No"),
                    confirmLabel: _t("Yes"),
                    confirm: () => {
                        window.localStorage.setItem("vivawallet_app_answer", "true");
                    },
                    cancel: () => {
                        window.localStorage.setItem("vivawallet_app_answer", "false");
                    },
                });

                return;
            }

            for (const lineUuid of this.currentOrder.payment_ids.map((line) => line.uuid)) {
                const paymentLine = this.currentOrder.getPaymentlineByUuid(lineUuid);
                if (this.vivaApp.use(paymentLine.payment_method_id) && !paymentLine.isDone()) {
                    paymentLine.delete();
                }
            }

            this.vivaApp.start(pm, this.isRefundOrder);
            return;
        }

        if (pm.use_payment_terminal === "viva_com" && this.isRefundOrder) {
            const refundedOrder = this.currentOrder.lines[0]?.refunded_orderline_id?.order_id;
            const amountDue = Math.abs(this.currentOrder.getDue());
            const matchedPaymentLine = refundedOrder.payment_ids.find(
                (line) =>
                    line.payment_method_id.use_payment_terminal === "viva_com" &&
                    line.amount === amountDue
            );
            if (matchedPaymentLine) {
                const paymentLineAddedSuccessfully = await super.addNewPaymentLine(pm);
                if (paymentLineAddedSuccessfully) {
                    const newPaymentLine = this.paymentLines.at(-1);
                    newPaymentLine.updateRefundPaymentLine(matchedPaymentLine);
                }
                return paymentLineAddedSuccessfully;
            }
        }

        return await super.addNewPaymentLine(pm);
    },
    deletePaymentLine(lineUuid) {
        const line = this.currentOrder.getPaymentlineByUuid(lineUuid);
        if (!line && !this.vivaApp.use(line.payment_method_id)) {
            return super.deletePaymentLine(lineUuid);
        }

        this.currentOrder.removePaymentline(line);
    },
    sendPaymentRequest(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return;
        }
        return super.sendPaymentRequest(line);
    },
    sendPaymentCancel(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return;
        }
        return super.sendPaymentCancel(line);
    },
    sendPaymentReverse(line) {
        if (this.vivaApp.use(line.payment_method_id)) {
            return;
        }
        return super.sendPaymentReverse(line);
    },
});
