/** @odoo-module */

import manageForm from '@payment/js/manage_form';
import stripeMixin from '@payment_stripe/js/stripe_mixin';

manageForm.include(stripeMixin);
manageForm.include({

    /**
     * @override method from payment_stripe.stripe_mixin
     * @private
     */
    _getElementsOptions() {
        return {
            ...this._super(...arguments),
            mode: 'setup',
            setupFutureUsage: 'off_session',
        };
    },

    /**
     * @override method from payment_stripe.stripe_mixin
     * @private
     * @param {object} processingValues - The processing values of the transaction.
     * @return {object} The processing error, if any.
     */
    async _stripeConfirmIntent(processingValues) {
        await this._super(...arguments);
        return await this.stripeJS.confirmSetup({
            elements: this.stripeElements,
            clientSecret: processingValues['client_secret'],
            confirmParams: {
                return_url: processingValues['return_url'],
            },
        });
    }
});
