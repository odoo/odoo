odoo.define('sale.payment_form', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const salePaymentMixin = {

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Add `sale_order_id` to the transaction route params if it is provided.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @param {string} provider - The provider of the selected payment option's acquirer
         * @param {number} paymentOptionId - The id of the selected payment option
         * @param {string} flow - The online payment flow of the selected payment option
         * @return {object} The extended transaction route params
         */
        _prepareTransactionRouteParams: function (provider, paymentOptionId, flow) {
            const transactionRouteParams = this._super(...arguments);
            return {
                ...transactionRouteParams,
                'sale_order_id': this.txContext.saleOrderId
                    ? parseInt(this.txContext.saleOrderId) : undefined,
            };
        },

    };

    checkoutForm.include(salePaymentMixin);
    manageForm.include(salePaymentMixin);

});
