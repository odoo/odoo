odoo.define('account_payment.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const PaymentMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Add `invoice_id` to the transaction route params if it is provided.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} code - The provider code of the selected payment option.
         * @param {number} paymentOptionId - The id of the selected payment option.
         * @param {string} flow - The online payment flow of the selected payment option.
         * @return {object} The extended transaction route params.
         */
        _prepareTransactionRouteParams: function (code, paymentOptionId, flow) {
            const transactionRouteParams = this._super(...arguments);
            return {
                ...transactionRouteParams,
                'invoice_id': this.txContext.invoiceId ? parseInt(this.txContext.invoiceId) : null,
            };
        },

    };

    checkoutForm.include(PaymentMixin);
    manageForm.include(PaymentMixin);

});
