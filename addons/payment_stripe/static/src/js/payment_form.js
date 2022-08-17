/* global Stripe */
odoo.define('payment_stripe.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const stripeMixin = {

        /**
         * Redirect the customer to Stripe hosted payment page.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The code of the payment option
         * @param {number} paymentOptionId - The id of the payment option handling the transaction
         * @param {object} processingValues - The processing values of the transaction
         * @return {undefined}
         */
        _processRedirectPayment: function (code, paymentOptionId, processingValues) {
            if (code !== 'stripe') {
                return this._super(...arguments);
            }

            const stripeJS = Stripe(processingValues['publishable_key'],
                this._prepareStripeOptions(processingValues));
            stripeJS.redirectToCheckout({
                sessionId: processingValues['session_id']
            });
        },

        /**
         * Prepare the options to init the Stripe JS Object
         *
         * Function overriden in internal module
         *
         * @param {object} processingValues
         * @return {object}
         */
        _prepareStripeOptions: function (processingValues) {
            return {};
        },
    };

    checkoutForm.include(stripeMixin);
    manageForm.include(stripeMixin);

    return stripeMixin;
});
