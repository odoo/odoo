import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PaymentForm } from "@payment/interactions/payment_form";

import { QFPayWalletDialog } from "@payment_qfpay/qfpay_wallet_dialog/qfpay_wallet_dialog";

patch(PaymentForm.prototype, {
    setup() {
        super.setup();
        this._paymentCancelled = false; // Track whether the user dismissed the wallet dialog.
    },

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of QFPay for direct payment.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "qfpay") {
            return super._prepareInlineForm(...arguments);
        }
        this._setPaymentFlow("direct");
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Process QFPay implementation of the direct payment flow.
     *
     * @override method from @payment/interactions/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "qfpay") {
            return super._processDirectFlow(...arguments);
        }

        try {
            await new Promise((resolve, reject) => {
                this.services.dialog.add(
                    QFPayWalletDialog,
                    {
                        sdkUrl: processingValues.sdk_url,
                        sdkEnv: processingValues.sdk_env,
                        sdkRegion: processingValues.sdk_region,
                        pickerPaymentType: processingValues.picker_payment_type,
                        paymentIntent: processingValues.payment_intent,
                        outTradeNo: processingValues.out_trade_no,
                        txamt: processingValues.txamt,
                        txcurrcd: processingValues.txcurrcd,
                        returnUrl: processingValues.return_url,
                        onPaymentComplete: resolve,
                    },
                    {
                        onClose: () => {
                            this._paymentCancelled = true;
                            this._enableButton();
                            reject();
                        },
                    }
                );
            });
        } catch (error) {
            if (!this._paymentCancelled) {
                this._displayErrorDialog(
                    _t("Payment Error"),
                    error?.message || _t("An unexpected error occurred during payment.")
                );
                this._enableButton();
            }
        }
        this._paymentCancelled = false;
    },
});
