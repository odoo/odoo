import { PaymentPostProcessing } from '@payment/interactions/post_processing';
import { patch } from '@web/core/utils/patch';

patch(PaymentPostProcessing, {

    /**
     * Don't wait for the transaction to be confirmed before redirecting customers to the landing
     * route, because custom transactions remain in the state 'pending' forever.
     *
     * @override method from `@payment/interactions/post_processing`
-    * @param {string} providerCode - The code of the provider handling the transaction.
     */
    getFinalStates(providerCode) {
        const finalStates = super.getFinalStates(...arguments);
        if (providerCode === 'custom') {
            finalStates.add('pending');
        }
        return finalStates;
    },

});
