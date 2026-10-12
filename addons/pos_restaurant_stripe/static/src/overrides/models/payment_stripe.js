import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PaymentStripe } from "@pos_stripe/app/payment_stripe";
import { patch } from "@web/core/utils/patch";

patch(PaymentStripe.prototype, {
    async captureAfterPayment(processPayment, line) {
        // Don't capture if the customer can tip, in that case we
        // will capture later.
        if (this.canBeAdjusted(line.uuid)) {
            return;
        }
        if (
            this.pos.config.set_tip_after_payment &&
            line.uiState.stripeOvercaptureSupported === false
        ) {
            await this.showOvercaptureNotSupportedError();
        }
        return super.captureAfterPayment(...arguments);
    },

    async showOvercaptureNotSupportedError() {
        const mcc = await this.pos.data.silentCall("pos.payment.method", "stripe_account_mcc", [
            [this.payment_method_id.id],
        ]);
        const mccMessage = mcc
            ? _t("Your current Stripe account's merchant category code (MCC) is %(mcc)s.", { mcc })
            : _t("Your current Stripe account's merchant category code (MCC) is not set.");
        const url =
            "https://docs.stripe.com/terminal/features/collecting-tips/on-receipt#availability";
        const link = markup`<a href="${url}" target="_blank">${_t("Stripe's documentation")}</a>`;
        this._showError(
            _t(
                "Tips can't be added to this Stripe payment. Stripe only allows tips after payment (overcapture) for certain merchant categories and card brands. %(mccMessage)s To check whether your business is eligible, see %(link)s or contact Stripe support.",
                { mccMessage, link }
            )
        );
    },

    async sendPaymentAdjust(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        this.capturePaymentStripe(line.transaction_id, line.amount, {
            stripe_currency_rounding: line.currency_id.rounding,
        });
    },

    canBeAdjusted(uuid) {
        var order = this.pos.getOrder();
        var line = order.getPaymentlineByUuid(uuid);
        return (
            this.pos.config.set_tip_after_payment &&
            line.payment_method_id.use_payment_terminal === "stripe" &&
            line.card_type !== "interac" &&
            line.uiState.stripeCardPresentNetwork !== "eftpos_au" &&
            line.uiState.stripeOvercaptureSupported !== false
        );
    },
});
