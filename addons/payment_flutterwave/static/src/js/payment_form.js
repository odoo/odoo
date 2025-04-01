import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    /**
     * Allow forcing redirect to authorization url for Flutterwave token flow.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    _processTokenFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode === 'flutterwave' && processingValues.redirect_form_html) {
            this._processRedirectFlow(...arguments);
        } else {
            this._super(...arguments);
        }
    }
});
