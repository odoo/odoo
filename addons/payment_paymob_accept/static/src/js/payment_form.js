import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    /**
     * Process the token payment flow.
     *
     * @private
     * @override
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processTokenFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode === 'paymob') {
            if (processingValues.paymob_token_redirect_url) {
                window.top.location.href = processingValues.paymob_token_redirect_url;
            } else {
                this._super(...arguments);
            }
        } else {
            this._super(...arguments);
        }
    },
});
