/** @odoo-module **/

import paymentPostProcessing from '@payment/js/post_processing';

paymentPostProcessing.include({
    /**
     * Don't wait for the transaction to be confirmed before redirecting customers to the
     * landing route because custom transactions remain in the state 'pending' forever.
     *
     * @override method from `@payment/js/post_processing`
     * @param {string} providerCode - The code of the provider handling the transaction.
     */
    _getFinalStates(providerCode) {
        const finalStates = this._super(...arguments);
        if (providerCode === 'custom') {
            finalStates.add('pending');
        }
        return finalStates;
    }
});
