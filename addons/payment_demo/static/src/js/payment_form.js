/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    // #=== DOM MANIPULATION ===#

    /**
     * Prepare the inline form of Demo for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'demo') {
            this._super(...arguments);
            return;
        } else if (flow === 'token') {
            return;
        }
        this._setPaymentFlow('direct');
    },

    // #=== PAYMENT FLOW ===#

    /**
     * Simulate a feedback from a payment provider and redirect the customer to the status page.
     *
     * @override method from payment.payment_form
     * @private
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {object} processingValues - The processing values of the transaction.
     * @return {void}
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'demo') {
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
        }).guardedCatch(error => {
            error.event.preventDefault();
            this._displayErrorDialog(_t("Payment processing failed"), error.message.data.message);
            this._enableButton(); // The button has been disabled before initiating the flow.
        });
    },

});
