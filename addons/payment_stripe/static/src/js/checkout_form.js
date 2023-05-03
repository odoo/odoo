/** @odoo-module */

import checkoutForm from '@payment/js/checkout_form';
import stripeMixin from '@payment_stripe/js/stripe_mixin';

checkoutForm.include(stripeMixin);
checkoutForm.include({

    /**
     * @override method from payment_stripe.stripe_mixin
     * @private
     */
    _getElementsOptions() {
        const elementsOptions =  {
            ...this._super(...arguments),
            mode: 'payment',
            amount: parseInt(this.stripeInlineFormValues['minor_amount']),
        };
        if (this.stripeInlineFormValues['is_tokenization_required']) {
            elementsOptions.setupFutureUsage = 'off_session';
        }
        return elementsOptions;
    },

    /**
     * @override method from payment_stripe.stripe_mixin
     * @private
     * @param {object} processingValues - The processing values of the transaction.
     * @return {object} The processing error, if any.
     */
    async _stripeConfirmIntent(processingValues) {
        await this._super(...arguments);
        return await this.stripeJS.confirmPayment({
            elements: this.stripeElements,
            clientSecret: processingValues['client_secret'],
            confirmParams: {
                return_url: processingValues['return_url'],
            },
        });
    },
});
