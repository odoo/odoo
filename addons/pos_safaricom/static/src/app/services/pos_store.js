import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("SAFARICOM_LATEST_RESPONSE", (payload) => {
            const paymentLine = this.models["pos.payment"].find(
                (line) =>
                    line.uiState?.safaricom_checkout_request_id === payload?.checkout_request_id &&
                    line.uiState?.safaricom_merchant_request_id === payload?.merchant_request_id
            );

            if (!paymentLine) {
                return;
            }
            // Get the payment interface
            const paymentMethod = paymentLine.payment_method_id;
            const paymentInterface = paymentMethod?.payment_terminal;

            // Update payment status based on callback
            if (payload.success) {
                paymentLine.transaction_id = payload.transaction_id;
                paymentLine.card_type = "M-Pesa";
                if (payload.phone_number) {
                    paymentLine.cardholder_name = payload.phone_number;
                }
                paymentLine.setPaymentStatus("done");

                // Complete the payment (resolve promise)
                if (paymentInterface?.completePayment) {
                    paymentInterface.completePayment(paymentLine, true);
                }
            } else {
                paymentLine.setPaymentStatus("retry");

                // Complete the payment (resolve promise)
                if (paymentInterface?.completePayment) {
                    paymentInterface.completePayment(paymentLine, false);
                }

                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Payment Failed"),
                    body: payload.result_desc || _t("Payment was not completed"),
                });
            }
        });
        this.data.connectWebSocket("NEW_LIPA_NA_MPESA_TRANSACTION", () => {
            this.lipaLastNotificationTime = Date.now();
        });
    },
});
