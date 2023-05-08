/** @odoo-module **/

import paymentForm from '@payment/js/payment_form';

paymentForm.include({

    // #=== PAYMENT FLOW ===#

    /**
     * Add `invoice_id` to the params for the RPC to the transaction route.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @return {object} The extended transaction route params.
     */
    _prepareTransactionRouteParams() {
        const transactionRouteParams = this._super(...arguments);
        return {
            ...transactionRouteParams,
            'invoice_id': this.paymentContext['invoiceId']
                ? parseInt(this.paymentContext['invoiceId']) : null,
        };
    },

});
