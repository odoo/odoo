/** @odoo-module */
/* global Stripe */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';
import { StripeOptions } from '@payment_stripe/js/stripe_options';

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

        const stripeJS = Stripe(
            processingValues['publishable_key'],
            // Instantiate the StripeOptions class to allow patching the method and add options.
            new StripeOptions()._prepareStripeOptions(processingValues),
        );
        stripeJS.redirectToCheckout({
            sessionId: processingValues['session_id']
        });
    },
};

checkoutForm.include(stripeMixin);
manageForm.include(stripeMixin);
