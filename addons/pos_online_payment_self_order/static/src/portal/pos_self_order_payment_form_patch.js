import { patch } from "@web/core/utils/patch";
import { PaymentForm } from "@payment/interactions/payment_form";
import { redirect } from "@web/core/utils/urls";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PaymentForm.prototype, {
    _prepareTransactionRouteParams() {
        const transactionRouteParams = super._prepareTransactionRouteParams();
        const regex = ["^/pos/pay/transaction/\\d+(\\?|$)"];
        if (regex.some((r) => new RegExp(r).test(this.paymentContext.transactionRoute || ""))) {
            transactionRouteParams["override_pending_payment"] = Boolean(
                this.overridePendingPayment
            );
        }
        return transactionRouteParams;
    },

    _handlePaymentProcessingError(processingValues) {
        if (processingValues.pos_online_payment_nothing_to_pay && processingValues.exit_route) {
            redirect(processingValues.exit_route);
            return;
        }
        if (processingValues.pos_online_payment_conflict) {
            this.services.dialog.add(ConfirmationDialog, {
                title: _t("Payment already in progress"),
                body: processingValues.state_message,
                confirmLabel: _t("Pay anyway"),
                confirm: () => {
                    this.overridePendingPayment = true;
                    this._initiatePaymentFlow(
                        this.paymentContext.providerCode,
                        this.paymentContext.paymentOptionId,
                        this.paymentContext.paymentMethodCode,
                        this.paymentContext.flow
                    );
                },
                cancel: () => this._enableButton(),
            });
            return;
        }
        return super._handlePaymentProcessingError(processingValues);
    },
});
