import { patch } from '@web/core/utils/patch';

import { PaymentForm } from '@payment/interactions/payment_form';
import { rpc, RPCError } from '@web/core/network/rpc';
import { _t } from '@web/core/l10n/translation';

patch(PaymentForm.prototype, {

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Safaricom for direct payment.
     *
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'safaricom') {
            await super._prepareInlineForm(...arguments);
            return;
        }

        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Trigger the payment processing by submitting the data.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The payment flow of the selected payment option.
     * @return {void}
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'safaricom') {
            // Tokens are handled by the generic flow
            await super._initiatePaymentFlow(...arguments);
            return;
        }

        const phoneNumber = document.querySelector('#o_safaricom_phone_number');
        if (!phoneNumber.reportValidity()) {
            this._enableButton(); // The submit button is disabled at this point, enable it
            return;
        }

        await super._initiatePaymentFlow(...arguments);
    },

    /**
     * Process the direct payment flow.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'safaricom') {
            await super._processDirectFlow(...arguments);
            return;
        }

        try {
            await this.waitFor(rpc('/payment/safaricom/payment', {
                'reference': processingValues.reference,
                'access_token': processingValues.access_token,
                'phone': document.querySelector('#o_safaricom_phone_number').value,
            }));
            window.location = '/payment/status';
        } catch (error) {
            const errorMessage = error instanceof RPCError ? error.data.message : error.message;
            this._displayErrorDialog(_t('Payment failed'), errorMessage);
            this._enableButton();
        }
    },
});
