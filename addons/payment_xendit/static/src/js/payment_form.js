/** @odoo-module */

import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    /**
     * Redirect the customer to complete a required 3-D Secure authentication for token payments.
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
        if (providerCode === 'xendit' && processingValues.pending_authentication_url) {
            // The authentication URL carries a required query string (the public API key). A
            // GET-method form submission discards and rebuilds it empty, and the page only
            // accepts GET (a POST submission is rejected with 405); navigate to it directly.
            const authUrl = new URL(
                processingValues.pending_authentication_url, window.location.href
            );
            if (authUrl.protocol === 'http:' || authUrl.protocol === 'https:') {
                // Navigate the top window rather than `window.location`, as the challenge page
                // (much like the bank's own 3DS pages) refuses to render inside a frame and
                // otherwise silently fails when the payment form itself is embedded in one (e.g.
                // the website builder's preview iframe), leaving the transaction stuck pending.
                window.top.location = authUrl.href;
            }
        } else {
            this._super(...arguments);
        }
    },

});
