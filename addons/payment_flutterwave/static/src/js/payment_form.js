odoo.define('payment_flutterwave.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const flutterwaveMixin = {
        /**
         * Allow forcing redirect to authorization url for Flutterwave token flow.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider_code - The code of the token's provider
         * @param {number} tokenId - The id of the token handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processTokenPayment: (provider_code, tokenId, processingValues) => {
            if (provider_code === 'flutterwave' && processingValues.auth_redirect_form_html) {
                // Append the redirect form to the body
                const $redirectForm = $(processingValues.auth_redirect_form_html).attr(
                    'id', 'o_payment_redirect_form'
                );

                // Authorization happens via POST instead of GET
                $redirectForm[0].setAttribute('method', 'post');

                // Ensures external redirections when in an iframe.
                $redirectForm[0].setAttribute('target', '_top');
                $(document.getElementsByTagName('body')[0]).append($redirectForm);

                // Submit the form
                $redirectForm.submit();
            } else {
                this._super(provider_code, tokenId, processingValues);
            }
        }
    };

    checkoutForm.include(flutterwaveMixin);
    manageForm.include(flutterwaveMixin);
});
