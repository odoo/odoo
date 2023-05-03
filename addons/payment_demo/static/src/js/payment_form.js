/** @odoo-module **/

import checkoutForm from '@payment/js/checkout_form';
import manageForm from '@payment/js/manage_form';

const paymentDemoMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
     *
     * @override method from @payment/js/payment_form_mixin
     * @private
     * @param {string} code - The code of the provider
     * @param {number} providerId - The id of the provider handling the transaction
     * @param {object} processingValues - The processing values of the transaction
     * @return {void}
     */
    _processDirectPayment: function (code, providerId, processingValues) {
        if (code !== 'demo') {
            this._super(...arguments);
            return;
        }

        const customerInput = document.getElementById('customer_input').value;
        const simulatedPaymentState = document.getElementById('simulated_payment_state').value;
        this._rpc({
            route: '/payment/demo/simulate_payment',
            params: {
                'reference': processingValues.reference,
                'payment_details': customerInput,
                'simulated_state': simulatedPaymentState,
            },
        }).then(() => {
            window.location = '/payment/status';
        });
    },

    /**
     * Prepare the inline form of Demo for direct payment.
     *
     * @override method from @payment/js/payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider
     * @param {integer} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {void}
     */
    _prepareInlineForm: function (code, paymentOptionId, flow) {
        if (code !== 'demo') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return;
        }
        this._setPaymentFlow('direct');
    },

};

checkoutForm.include(paymentDemoMixin);
manageForm.include(paymentDemoMixin);
