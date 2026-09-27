import { PaymentStatus } from '@payment/interactions/payment_status';
import { patch } from '@web/core/utils/patch';

patch(PaymentStatus, {

    /**
     * Don't wait for the transaction to be confirmed before redirecting customers to the landing
     * route, because custom transactions remain in the state 'pending' forever.
     *
     * @override method from `@payment/interactions/payment_status`
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
