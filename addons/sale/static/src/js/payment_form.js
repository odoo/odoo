/** @odoo-module **/

import checkoutForm from '@payment/js/checkout_form';
import manageForm from '@payment/js/manage_form';

const salePaymentMixin = {

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add `sale_order_id` to the transaction route params if it is provided.
     *
     * @override method from @payment/js/payment_form_mixin
     * @private
     * @param {string} code - The code of the selected payment option's provider
     * @param {number} paymentOptionId - The id of the selected payment option
     * @param {string} flow - The online payment flow of the selected payment option
     * @return {object} The extended transaction route params
     */
    _prepareTransactionRouteParams: function (code, paymentOptionId, flow) {
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
