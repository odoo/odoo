/* global bolt */

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { PaymentForm } from "@payment/interactions/payment_form";

patch(PaymentForm.prototype, {
    // #=== DOM MANIPULATION ===#

    /**
     * Update the payment context to set the flow to 'direct'.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */

    async _prepareInlineForm(providerId, providerCode, paymentOptionId, _paymentMethodCode, flow) {
        if (providerCode !== "payu") {
            await super._prepareInlineForm(...arguments);
            return;
        }

        // Overwrite the flow of the select payment method.
        this._setPaymentFlow("direct");
    },

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "payu") {
            await super._processDirectFlow(...arguments);
            return;
        }
        const { txn_env, payload } = processingValues;

        // Load SDK
        const sdkUrl =
            txn_env === "prod"
                ? "https://jssdk.payu.in/bolt/bolt.min.js"
                : "https://jssdk-uat.payu.in/bolt/bolt.min.js";

        await loadJS(sdkUrl);

        // Define event handlers
        const handlers = {
            responseHandler: (BOLT) => {
                if (BOLT.response.txnStatus === "SUCCESS") {
                    window.location = "/payment/status";
                } else {
                    window.location.reload();
                }
            },
            catchException: (BOLT) => {
                console.error("Exception:", BOLT);
                this._displayErrorDialog("PayU Error:", BOLT.message);
            },
        };
        try {
            bolt.launch(payload, handlers);
        } catch (error) {
            console.error(error);
            this._displayErrorDialog("PayU Error:", error.message);
        }
    },
});
