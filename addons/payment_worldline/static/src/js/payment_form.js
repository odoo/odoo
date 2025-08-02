/** @odoo-module */

import checkoutForm from 'payment.checkout_form';
import manageForm from 'payment.manage_form';

const worldlineMixin = {

    /**
     * Allow forcing redirect to 3-D Secure authentication for Ogone token flow.
     *
     * @override method from payment.payment_form_mixin
     * @private
     * @param {string} provider_code - The code of the token's provider
     * @param {number} tokenId - The id of the token handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {undefined}
     */
    _processTokenPayment: function (provider_code, tokenId, processingValues) {
        if (provider_code === 'worldline' && processingValues.force_flow === 'redirect') {
            delete processingValues.force_flow;
            this._processRedirectPayment(...arguments);
        } else {
            this._super(...arguments);
        }
    }
};

checkoutForm.include(worldlineMixin);
manageForm.include(worldlineMixin);
