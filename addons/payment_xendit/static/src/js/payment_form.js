odoo.define('payment_xendit.payment_form', function (require) {
    'use strict';
    const checkoutForm = require('payment.checkout_form');
    const manageForm = require('payment.manage_form');

    const xenditMixin = {
        /**
         * Payment processing speicific to Xendit
         *
         * @param {string} provider Payment provider name
         * @param {number} paymentOptionId The id of payment provider used
         * @param {string} flow The online payment flow of the transaction
         * @returns {Promise}
         */
        _processPayment(provider, paymentOptionId, flow) {
            if (provider !== 'xendit' || flow === 'token') {
                return this._super(...arguments); // Tokens are handled by the generic flow
            }
            return this._rpc({
                route: this.txContext.transactionRoute,
                params: this._prepareTransactionRouteParams(provider, paymentOptionId, flow),
            }).then(processingValues =>{
                return this._rpc({
                    route: '/payment/xendit/payment_methods',
                    params: {
                        "provider_id": paymentOptionId,
                        "reference": processingValues.reference,
                        "amount": processingValues.amount,
                        "currency_id": processingValues.currency_id,
                        "partner_id": processingValues.partner_id,
                    }
                })
            }).then(paymentResponse => {
                // simulate redirect form submission to access the URL (avoiding cross-origin caused by iframe)
                const $redirectForm = $('<form></form>').attr('id', 'o_payment_redirect_form')
                $redirectForm[0].setAttribute('target', '_top');
                $redirectForm[0].setAttribute('action', paymentResponse.url);
                $(document.getElementsByTagName('body')[0]).append($redirectForm);

                $redirectForm.submit()
            });
        },
    }
    
    checkoutForm.include(xenditMixin);
    manageForm.include(xenditMixin);
})
